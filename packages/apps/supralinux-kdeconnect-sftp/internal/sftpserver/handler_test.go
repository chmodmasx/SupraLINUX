// SPDX-License-Identifier: GPL-2.0-or-later
// SPDX-FileCopyrightText: 2026 SupraLINUX Project

package sftpserver

import (
	"errors"
	"io"
	"os"
	"path/filepath"
	"testing"

	"github.com/pkg/sftp"
)

const (
	openRead  = 0x00000001
	openWrite = 0x00000002
	openCreat = 0x00000008
	openTrunc = 0x00000010
)

func newTestHandler(t *testing.T, readOnly bool) (*Handler, string) {
	t.Helper()
	root := t.TempDir()
	handler, err := NewHandler(root, readOnly)
	if err != nil {
		t.Fatal(err)
	}
	return handler, root
}

func TestMapPathStaysInsideRoot(t *testing.T) {
	handler, root := newTestHandler(t, false)

	inside, err := handler.mapPath("/sub/../file.txt", false)
	if err != nil {
		t.Fatal(err)
	}
	if want := filepath.Join(root, "file.txt"); inside != want {
		t.Fatalf("mapPath = %q, want %q", inside, want)
	}

	for _, virtual := range []string{"/../../etc/passwd", "/../outside", "/..", "/../.."} {
		got, err := handler.mapPath(virtual, false)
		if err != nil {
			continue
		}
		if !within(root, got) {
			t.Fatalf("mapPath(%q) escaped root: %q", virtual, got)
		}
	}
}

func TestMapPathRejectsSymlinkEscape(t *testing.T) {
	handler, root := newTestHandler(t, false)
	outside := t.TempDir()
	if err := os.WriteFile(filepath.Join(outside, "secret"), []byte("secret"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "escape")); err != nil {
		t.Fatal(err)
	}

	if _, err := handler.mapPath("/escape/secret", true); !errors.Is(err, os.ErrPermission) {
		t.Fatalf("expected permission error, got %v", err)
	}
	if _, err := handler.Fileread(&sftp.Request{Method: "Get", Filepath: "/escape/secret", Flags: openRead}); !errors.Is(err, os.ErrPermission) {
		t.Fatalf("expected permission error from Fileread, got %v", err)
	}

	linkPath, err := handler.mapPath("/escape", false)
	if err != nil {
		t.Fatal(err)
	}
	if linkPath != filepath.Join(root, "escape") {
		t.Fatalf("lstat path = %q", linkPath)
	}
}

func TestFilewriteRejectsDanglingSymlinkEscape(t *testing.T) {
	handler, root := newTestHandler(t, false)
	outside := t.TempDir()
	if err := os.Symlink(filepath.Join(outside, "missing"), filepath.Join(root, "dangling")); err != nil {
		t.Fatal(err)
	}

	if _, err := handler.Filewrite(&sftp.Request{Method: "Put", Filepath: "/dangling", Flags: openWrite | openCreat}); !errors.Is(err, os.ErrPermission) {
		t.Fatalf("expected permission error from Filewrite, got %v", err)
	}
	if _, err := handler.OpenFile(&sftp.Request{Method: "Put", Filepath: "/dangling", Flags: openWrite | openCreat}); !errors.Is(err, os.ErrPermission) {
		t.Fatalf("expected permission error from OpenFile, got %v", err)
	}
	if _, err := os.Lstat(filepath.Join(outside, "missing")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("dangling symlink target was created: %v", err)
	}
}

func TestMapPathAllowsSymlinkInsideRoot(t *testing.T) {
	handler, root := newTestHandler(t, false)
	if err := os.WriteFile(filepath.Join(root, "target.txt"), []byte("hello"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink("target.txt", filepath.Join(root, "link.txt")); err != nil {
		t.Fatal(err)
	}

	resolved, err := handler.mapPath("/link.txt", true)
	if err != nil {
		t.Fatal(err)
	}
	if resolved != filepath.Join(root, "target.txt") {
		t.Fatalf("resolved = %q", resolved)
	}
}

func TestFileReadWriteAndList(t *testing.T) {
	handler, root := newTestHandler(t, false)

	writer, err := handler.Filewrite(&sftp.Request{Method: "Put", Filepath: "/hello.txt", Flags: openWrite | openCreat | openTrunc})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := writer.WriteAt([]byte("hello world"), 0); err != nil {
		t.Fatal(err)
	}
	if closer, ok := writer.(io.Closer); ok {
		if err := closer.Close(); err != nil {
			t.Fatal(err)
		}
	}

	if data, err := os.ReadFile(filepath.Join(root, "hello.txt")); err != nil || string(data) != "hello world" {
		t.Fatalf("file content = %q, err = %v", data, err)
	}

	reader, err := handler.Fileread(&sftp.Request{Method: "Get", Filepath: "/hello.txt", Flags: openRead})
	if err != nil {
		t.Fatal(err)
	}
	data, err := io.ReadAll(io.NewSectionReader(reader, 0, 1<<20))
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "hello world" {
		t.Fatalf("read = %q", data)
	}

	entries, err := handler.Filelist(&sftp.Request{Method: "List", Filepath: "/"})
	if err != nil {
		t.Fatal(err)
	}
	buffer := make([]os.FileInfo, 8)
	n, err := entries.ListAt(buffer, 0)
	if err != nil && !errors.Is(err, io.EOF) {
		t.Fatal(err)
	}
	found := false
	for _, entry := range buffer[:n] {
		if entry.Name() == "hello.txt" {
			found = true
		}
	}
	if !found {
		t.Fatal("hello.txt not listed")
	}
}

func TestReadlinkSanitizesTargets(t *testing.T) {
	handler, root := newTestHandler(t, false)
	if err := os.WriteFile(filepath.Join(root, "hello.txt"), []byte("hello"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink("hello.txt", filepath.Join(root, "inside.txt")); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink("/etc/passwd", filepath.Join(root, "absolute.txt")); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink("../outside", filepath.Join(root, "escaping.txt")); err != nil {
		t.Fatal(err)
	}

	target, err := handler.Readlink("/inside.txt")
	if err != nil {
		t.Fatal(err)
	}
	if target != "hello.txt" {
		t.Fatalf("inside target = %q", target)
	}

	target, err = handler.Readlink("/absolute.txt")
	if err != nil {
		t.Fatal(err)
	}
	if target != "etc/passwd" {
		t.Fatalf("absolute target = %q, want etc/passwd", target)
	}
	if _, err := handler.Fileread(&sftp.Request{Method: "Get", Filepath: "/etc/passwd", Flags: openRead}); err == nil {
		t.Fatal("host /etc/passwd must not be reachable through the virtual root")
	}

	if _, err := handler.Readlink("/escaping.txt"); !errors.Is(err, os.ErrPermission) {
		t.Fatalf("escaping target error = %v", err)
	}
}

func TestFileCommands(t *testing.T) {
	handler, root := newTestHandler(t, false)
	if err := os.WriteFile(filepath.Join(root, "old.txt"), []byte("data"), 0o600); err != nil {
		t.Fatal(err)
	}

	if err := handler.Filecmd(&sftp.Request{Method: "Mkdir", Filepath: "/dir"}); err != nil {
		t.Fatal(err)
	}
	if info, err := os.Stat(filepath.Join(root, "dir")); err != nil || !info.IsDir() {
		t.Fatalf("mkdir failed: %v", err)
	}

	if err := handler.Filecmd(&sftp.Request{Method: "Rename", Filepath: "/old.txt", Target: "/new.txt"}); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(root, "new.txt")); err != nil {
		t.Fatal(err)
	}

	if err := handler.Filecmd(&sftp.Request{Method: "Symlink", Filepath: "/new.txt", Target: "/link.txt"}); err != nil {
		t.Fatal(err)
	}
	target, err := os.Readlink(filepath.Join(root, "link.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if target != "new.txt" {
		t.Fatalf("symlink target = %q, want new.txt", target)
	}

	if err := handler.Filecmd(&sftp.Request{Method: "Remove", Filepath: "/link.txt"}); err != nil {
		t.Fatal(err)
	}
	if err := handler.Filecmd(&sftp.Request{Method: "Remove", Filepath: "/new.txt"}); err != nil {
		t.Fatal(err)
	}
	if err := handler.Filecmd(&sftp.Request{Method: "Rmdir", Filepath: "/dir"}); err != nil {
		t.Fatal(err)
	}
}

func TestReadOnlyRejectsWrites(t *testing.T) {
	handler, _ := newTestHandler(t, true)
	if _, err := handler.Filewrite(&sftp.Request{Method: "Put", Filepath: "/new.txt", Flags: openWrite | openCreat}); !errors.Is(err, os.ErrPermission) {
		t.Fatalf("Filewrite error = %v", err)
	}
	if err := handler.Filecmd(&sftp.Request{Method: "Mkdir", Filepath: "/newdir"}); !errors.Is(err, os.ErrPermission) {
		t.Fatalf("Mkdir error = %v", err)
	}
}

func TestStatVFS(t *testing.T) {
	handler, _ := newTestHandler(t, false)
	stat, err := handler.StatVFS(&sftp.Request{Method: "StatVFS", Filepath: "/"})
	if err != nil {
		t.Fatal(err)
	}
	if stat.Bsize == 0 || stat.Blocks == 0 {
		t.Fatalf("unexpected statvfs: %+v", stat)
	}
}

func TestRealPath(t *testing.T) {
	handler, _ := newTestHandler(t, false)
	got, err := handler.RealPath("../sub/./file")
	if err != nil {
		t.Fatal(err)
	}
	if got != "/sub/file" {
		t.Fatalf("RealPath = %q", got)
	}
}
