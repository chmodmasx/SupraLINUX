// SPDX-License-Identifier: GPL-2.0-or-later
// SPDX-FileCopyrightText: 2026 SupraLINUX Project

package sftpserver

import (
	"bytes"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"errors"
	"fmt"
	"os"

	"golang.org/x/crypto/ssh"
)

// ReadAuthorizedKeyFile reads the public key of the paired KDE Connect
// device.  The file may contain either an OpenSSH authorized_keys line or a
// PEM public key/certificate as exported by QSslCertificate::publicKey().
func ReadAuthorizedKeyFile(path string) (ssh.PublicKey, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read authorized key: %w", err)
	}
	key, err := ParseAuthorizedKey(data)
	if err != nil {
		return nil, fmt.Errorf("parse authorized key: %w", err)
	}
	return key, nil
}

// ParseAuthorizedKey accepts the formats emitted by KDE Connect and
// ssh-keygen: an OpenSSH authorized_keys line, a PKIX PEM public key, a
// PKCS#1 RSA public key, or an X.509 certificate.
func ParseAuthorizedKey(data []byte) (ssh.PublicKey, error) {
	data = bytes.TrimSpace(data)
	if len(data) == 0 {
		return nil, errors.New("empty public key")
	}

	if key, _, _, rest, err := ssh.ParseAuthorizedKey(data); err == nil && len(bytes.TrimSpace(rest)) == 0 {
		return key, nil
	}

	for rest := data; len(rest) > 0; {
		var block *pem.Block
		block, rest = pem.Decode(rest)
		if block == nil {
			break
		}

		var publicKey any
		switch block.Type {
		case "PUBLIC KEY":
			parsed, err := x509.ParsePKIXPublicKey(block.Bytes)
			if err != nil {
				return nil, fmt.Errorf("parse PKIX public key: %w", err)
			}
			publicKey = parsed
		case "RSA PUBLIC KEY":
			parsed, err := x509.ParsePKCS1PublicKey(block.Bytes)
			if err != nil {
				return nil, fmt.Errorf("parse PKCS#1 public key: %w", err)
			}
			publicKey = parsed
		case "CERTIFICATE":
			cert, err := x509.ParseCertificate(block.Bytes)
			if err != nil {
				return nil, fmt.Errorf("parse certificate: %w", err)
			}
			publicKey = cert.PublicKey
		default:
			continue
		}

		key, err := ssh.NewPublicKey(publicKey)
		if err != nil {
			return nil, fmt.Errorf("convert public key: %w", err)
		}
		return key, nil
	}

	return nil, errors.New("unsupported public key format")
}

// NewHostSigner creates an ephemeral SSH host key.  KDE Connect's sshfs
// invocation disables host-key verification, so the key only needs to be
// valid for the lifetime of the session.
func NewHostSigner() (ssh.Signer, error) {
	_, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, fmt.Errorf("generate host key: %w", err)
	}
	signer, err := ssh.NewSignerFromKey(privateKey)
	if err != nil {
		return nil, fmt.Errorf("create host signer: %w", err)
	}
	return signer, nil
}

// KeysEqual compares two SSH public keys without depending on their concrete
// algorithm type.
func KeysEqual(a, b ssh.PublicKey) bool {
	if a == nil || b == nil {
		return false
	}
	return bytes.Equal(a.Marshal(), b.Marshal())
}
