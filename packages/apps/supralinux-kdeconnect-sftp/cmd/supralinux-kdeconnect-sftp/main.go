// SPDX-License-Identifier: GPL-2.0-or-later
// SPDX-FileCopyrightText: 2026 SupraLINUX Project

// supralinux-kdeconnect-sftp is an ephemeral, single-user SFTP server
// launched by the KDE Connect sftp plugin.  It is not a system service.
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"os/user"
	"syscall"
	"time"

	"supralinux.local/kdeconnect-sftp/internal/sftpserver"
)

func main() {
	logger := log.New(os.Stderr, "supralinux-kdeconnect-sftp: ", log.LstdFlags)

	home, _ := os.UserHomeDir()
	currentUser := os.Getenv("USER")
	if currentUser == "" {
		if entry, err := user.Current(); err == nil {
			currentUser = entry.Username
		}
	}

	var (
		listen        string
		root          string
		username      string
		authorizedKey string
		readOnly      bool
		idleTimeout   time.Duration
		startTimeout  time.Duration
		maxLifetime   time.Duration
	)
	flag.StringVar(&listen, "listen", "127.0.0.1:0", "IP:port to listen on (port 0 selects a free port)")
	flag.StringVar(&root, "root", home, "directory tree to expose")
	flag.StringVar(&username, "user", currentUser, "SSH username accepted by the server")
	flag.StringVar(&authorizedKey, "authorized-key-file", "", "file with the paired device's public key")
	flag.BoolVar(&readOnly, "read-only", false, "deny all filesystem modifications")
	flag.DurationVar(&idleTimeout, "idle-timeout", 2*time.Minute, "stop after this long with no active client")
	flag.DurationVar(&startTimeout, "startup-timeout", 60*time.Second, "stop if no client connects within this time")
	flag.DurationVar(&maxLifetime, "max-lifetime", 8*time.Hour, "maximum lifetime of the server")
	flag.Parse()

	if authorizedKey == "" {
		logger.Fatal("--authorized-key-file is required")
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := sftpserver.Config{
		ListenAddr:        listen,
		Root:              root,
		User:              username,
		AuthorizedKeyFile: authorizedKey,
		ReadOnly:          readOnly,
		IdleTimeout:       idleTimeout,
		StartupTimeout:    startTimeout,
		MaxLifetime:       maxLifetime,
		Logger:            logger,
		OnReady: func(addr net.Addr) {
			_, port, err := net.SplitHostPort(addr.String())
			if err != nil {
				logger.Printf("listening on %s", addr)
				return
			}
			fmt.Fprintf(os.Stdout, "PORT=%s\n", port)
			_ = os.Stdout.Sync()
			logger.Printf("listening on %s", addr)
		},
	}

	if err := sftpserver.Run(ctx, cfg); err != nil {
		logger.Fatal(err)
	}
}
