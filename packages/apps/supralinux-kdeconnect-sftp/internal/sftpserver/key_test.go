// SPDX-License-Identifier: GPL-2.0-or-later
// SPDX-FileCopyrightText: 2026 SupraLINUX Project

package sftpserver

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"testing"
	"time"

	"golang.org/x/crypto/ssh"
)

func TestParseAuthorizedKeyOpenSSH(t *testing.T) {
	publicKey, _, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	sshKey, err := ssh.NewPublicKey(publicKey)
	if err != nil {
		t.Fatal(err)
	}
	encoded := ssh.MarshalAuthorizedKey(sshKey)

	parsed, err := ParseAuthorizedKey(encoded)
	if err != nil {
		t.Fatal(err)
	}
	if !KeysEqual(parsed, sshKey) {
		t.Fatal("parsed key does not match")
	}
}

func TestParseAuthorizedKeyPEM(t *testing.T) {
	publicKey, _, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	der, err := x509.MarshalPKIXPublicKey(publicKey)
	if err != nil {
		t.Fatal(err)
	}
	encoded := pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: der})

	parsed, err := ParseAuthorizedKey(encoded)
	if err != nil {
		t.Fatal(err)
	}
	sshKey, err := ssh.NewPublicKey(publicKey)
	if err != nil {
		t.Fatal(err)
	}
	if !KeysEqual(parsed, sshKey) {
		t.Fatal("parsed key does not match")
	}
}

func TestParseAuthorizedKeyCertificate(t *testing.T) {
	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	template := &x509.Certificate{
		SerialNumber:          big.NewInt(1),
		Subject:               pkix.Name{CommonName: "test-device"},
		NotBefore:             time.Now().Add(-time.Minute),
		NotAfter:              time.Now().Add(time.Hour),
		KeyUsage:              x509.KeyUsageDigitalSignature,
		BasicConstraintsValid: true,
	}
	der, err := x509.CreateCertificate(rand.Reader, template, template, publicKey, privateKey)
	if err != nil {
		t.Fatal(err)
	}
	encoded := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der})

	parsed, err := ParseAuthorizedKey(encoded)
	if err != nil {
		t.Fatal(err)
	}
	sshKey, err := ssh.NewPublicKey(publicKey)
	if err != nil {
		t.Fatal(err)
	}
	if !KeysEqual(parsed, sshKey) {
		t.Fatal("parsed key does not match")
	}
}

func TestParseAuthorizedKeyRejectsGarbage(t *testing.T) {
	if _, err := ParseAuthorizedKey([]byte("not a public key")); err == nil {
		t.Fatal("expected an error")
	}
}

func TestNewHostSigner(t *testing.T) {
	signer, err := NewHostSigner()
	if err != nil {
		t.Fatal(err)
	}
	if signer.PublicKey() == nil {
		t.Fatal("empty host key")
	}
}
