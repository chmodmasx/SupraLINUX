// SPDX-License-Identifier: GPL-2.0-or-later
// SPDX-FileCopyrightText: 2026 SupraLINUX Project

package sftpserver

import (
	"context"
	"fmt"
	"log"
	"net"
	"os"
	"sync"
	"sync/atomic"
	"time"

	"github.com/pkg/sftp"
	"golang.org/x/crypto/ssh"
	"golang.org/x/sys/unix"
)

// Config describes one ephemeral SFTP server instance.
type Config struct {
	ListenAddr        string
	Root              string
	User              string
	AuthorizedKeyFile string
	ReadOnly          bool
	IdleTimeout       time.Duration
	StartupTimeout    time.Duration
	MaxLifetime       time.Duration
	Logger            *log.Logger
	OnReady           func(net.Addr)
}

// Server is a single-user SFTP server.  It accepts the paired device's
// public key, permits only the "sftp" subsystem, and exits when the client
// disappears or the configured lifetime expires.
type Server struct {
	cfg        Config
	handler    *Handler
	sshConfig  *ssh.ServerConfig
	listener   net.Listener
	logger     *log.Logger
	active     atomic.Int32
	seen       atomic.Bool
	mu         sync.Mutex
	conns      map[net.Conn]struct{}
	idleTimer  *time.Timer
	startTimer *time.Timer
	maxTimer   *time.Timer
	stopOnce   sync.Once
	stopCtx    context.CancelFunc
}

// Run creates and serves the SFTP server until the context is cancelled or
// the lifecycle timers expire.
func Run(ctx context.Context, cfg Config) error {
	if cfg.ListenAddr == "" {
		cfg.ListenAddr = "127.0.0.1:0"
	}
	if cfg.Root == "" {
		return fmt.Errorf("root is required")
	}
	if cfg.User == "" {
		return fmt.Errorf("user is required")
	}
	if cfg.AuthorizedKeyFile == "" {
		return fmt.Errorf("authorized key file is required")
	}
	if cfg.IdleTimeout <= 0 {
		cfg.IdleTimeout = 2 * time.Minute
	}
	if cfg.StartupTimeout <= 0 {
		cfg.StartupTimeout = 60 * time.Second
	}
	if cfg.MaxLifetime <= 0 {
		cfg.MaxLifetime = 8 * time.Hour
	}
	if cfg.Logger == nil {
		cfg.Logger = log.New(os.Stderr, "supralinux-kdeconnect-sftp: ", log.LstdFlags)
	}

	// If kdeconnectd dies, do not leave the SFTP listener behind.
	if err := unix.Prctl(unix.PR_SET_PDEATHSIG, uintptr(unix.SIGTERM), 0, 0, 0); err != nil {
		cfg.Logger.Printf("warning: PR_SET_PDEATHSIG: %v", err)
	}

	publicKey, err := ReadAuthorizedKeyFile(cfg.AuthorizedKeyFile)
	if err != nil {
		return err
	}
	handler, err := NewHandler(cfg.Root, cfg.ReadOnly)
	if err != nil {
		return err
	}
	signer, err := NewHostSigner()
	if err != nil {
		return err
	}

	sshConfig := &ssh.ServerConfig{
		ServerVersion: "SSH-2.0-SupraLINUX_KDEConnect_SFTP",
		MaxAuthTries:  3,
		PublicKeyCallback: func(conn ssh.ConnMetadata, key ssh.PublicKey) (*ssh.Permissions, error) {
			if conn.User() != cfg.User {
				return nil, fmt.Errorf("unknown user")
			}
			if !KeysEqual(key, publicKey) {
				return nil, fmt.Errorf("unauthorized key")
			}
			return nil, nil
		},
	}
	sshConfig.AddHostKey(signer)

	listener, err := net.Listen("tcp", cfg.ListenAddr)
	if err != nil {
		return fmt.Errorf("listen: %w", err)
	}

	server := &Server{
		cfg:       cfg,
		handler:   handler,
		sshConfig: sshConfig,
		listener:  listener,
		logger:    cfg.Logger,
		conns:     make(map[net.Conn]struct{}),
	}
	if cfg.OnReady != nil {
		cfg.OnReady(listener.Addr())
	}
	return server.serve(ctx)
}

func (s *Server) serve(ctx context.Context) error {
	ctx, cancel := context.WithCancel(ctx)
	s.stopCtx = cancel
	defer cancel()

	s.startTimer = time.AfterFunc(s.cfg.StartupTimeout, func() {
		if s.active.Load() == 0 {
			s.logger.Printf("no client connected within %s", s.cfg.StartupTimeout)
			s.stop()
		}
	})
	s.maxTimer = time.AfterFunc(s.cfg.MaxLifetime, func() {
		s.logger.Printf("maximum lifetime %s reached", s.cfg.MaxLifetime)
		s.stop()
	})

	go func() {
		<-ctx.Done()
		s.stop()
	}()

	var wait sync.WaitGroup
	for {
		conn, err := s.listener.Accept()
		if err != nil {
			if ctx.Err() != nil {
				break
			}
			s.stop()
			wait.Wait()
			return err
		}

		if s.startTimer != nil {
			s.startTimer.Stop()
		}
		s.stopIdleTimer()
		s.seen.Store(true)
		s.trackConn(conn)
		s.active.Add(1)
		wait.Add(1)
		go func() {
			defer wait.Done()
			defer func() {
				s.untrackConn(conn)
				s.active.Add(-1)
				s.connectionFinished()
			}()
			s.handleConn(conn)
		}()
	}

	wait.Wait()
	return nil
}

func (s *Server) handleConn(conn net.Conn) {
	_ = conn.SetDeadline(time.Now().Add(30 * time.Second))
	sshConn, channels, requests, err := ssh.NewServerConn(conn, s.sshConfig)
	if err != nil {
		s.logger.Printf("ssh handshake failed: %v", err)
		return
	}
	defer sshConn.Close()
	_ = conn.SetDeadline(time.Time{})

	s.logger.Printf("client connected from %s", sshConn.RemoteAddr())
	go ssh.DiscardRequests(requests)

	for newChannel := range channels {
		if newChannel.ChannelType() != "session" {
			_ = newChannel.Reject(ssh.UnknownChannelType, "only session channels are allowed")
			continue
		}
		channel, channelRequests, err := newChannel.Accept()
		if err != nil {
			s.logger.Printf("accept session channel: %v", err)
			continue
		}
		go s.handleSession(channel, channelRequests)
	}
}

func (s *Server) handleSession(channel ssh.Channel, requests <-chan *ssh.Request) {
	defer channel.Close()

	for request := range requests {
		switch request.Type {
		case "subsystem":
			var payload struct {
				Subsystem string
			}
			if err := ssh.Unmarshal(request.Payload, &payload); err != nil || payload.Subsystem != "sftp" {
				_ = request.Reply(false, nil)
				continue
			}
			if err := request.Reply(true, nil); err != nil {
				return
			}
			server := sftp.NewRequestServer(channel, sftp.Handlers{
				FileGet:  s.handler,
				FilePut:  s.handler,
				FileCmd:  s.handler,
				FileList: s.handler,
			}, sftp.WithStartDirectory("/"))
			err := server.Serve()
			if err != nil && err.Error() != "EOF" {
				s.logger.Printf("sftp session ended: %v", err)
			}
			return
		case "env", "window-change", "signal":
			_ = request.Reply(false, nil)
		default:
			// Never accept exec, shell, pty-req or forwarding requests.
			_ = request.Reply(false, nil)
		}
	}
}

func (s *Server) trackConn(conn net.Conn) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.conns[conn] = struct{}{}
}

func (s *Server) untrackConn(conn net.Conn) {
	s.mu.Lock()
	delete(s.conns, conn)
	s.mu.Unlock()
}

func (s *Server) connectionFinished() {
	if s.active.Load() != 0 || !s.seen.Load() {
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.idleTimer != nil {
		s.idleTimer.Stop()
	}
	s.idleTimer = time.AfterFunc(s.cfg.IdleTimeout, func() {
		if s.active.Load() == 0 {
			s.logger.Printf("no active client for %s, stopping", s.cfg.IdleTimeout)
			s.stop()
		}
	})
}

func (s *Server) stopIdleTimer() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.idleTimer != nil {
		s.idleTimer.Stop()
		s.idleTimer = nil
	}
}

func (s *Server) stop() {
	s.stopOnce.Do(func() {
		if s.stopCtx != nil {
			s.stopCtx()
		}
		if s.startTimer != nil {
			s.startTimer.Stop()
		}
		if s.maxTimer != nil {
			s.maxTimer.Stop()
		}
		s.stopIdleTimer()
		_ = s.listener.Close()
		s.mu.Lock()
		for conn := range s.conns {
			_ = conn.Close()
		}
		s.conns = make(map[net.Conn]struct{})
		s.mu.Unlock()
	})
}
