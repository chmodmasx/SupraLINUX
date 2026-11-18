// SPDX-License-Identifier: GPL-2.0-or-later
// SPDX-FileCopyrightText: 2026 SupraLINUX Project

package sftpserver

import (
	"errors"
	"io"
	"os"
	"path"
	"path/filepath"
	"strings"

	"github.com/pkg/sftp"
	"golang.org/x/sys/unix"
)

// Handler serves a single directory tree through SFTP.  Paths are interpreted
// as virtual absolute paths rooted at root; symlinks that resolve outside root
// are rejected.  The process runs as the desktop user, so the kernel still
// enforces the user's permissions.
type Handler struct {
	root     string
	readOnly bool
}

// NewHandler creates a native filesystem handler rooted at root.
func NewHandler(root string, readOnly bool) (*Handler, error) {
	absolute, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}
	resolved, err := filepath.EvalSymlinks(absolute)
	if err == nil {
		absolute = resolved
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	info, err := os.Stat(absolute)
	if err != nil {
		return nil, err
	}
	if !info.IsDir() {
		return nil, &os.PathError{Op: "root", Path: absolute, Err: unix.ENOTDIR}
	}
	return &Handler{root: absolute, readOnly: readOnly}, nil
}

func (h *Handler) Fileread(r *sftp.Request) (io.ReaderAt, error) {
	if !r.Pflags().Read {
		return nil, os.ErrPermission
	}
	local, err := h.mapPath(r.Filepath, true)
	if err != nil {
		return nil, err
	}
	return os.OpenFile(local, os.O_RDONLY, 0)
}

func (h *Handler) Filewrite(r *sftp.Request) (io.WriterAt, error) {
	flags := r.Pflags()
	if !flags.Write || h.readOnly {
		return nil, os.ErrPermission
	}
	local, err := h.mapPath(r.Filepath, true)
	if err != nil {
		return nil, err
	}
	if err := rejectFinalSymlink(local); err != nil {
		return nil, err
	}
	osFlags := os.O_WRONLY | unix.O_NOFOLLOW
	if flags.Creat {
		osFlags |= os.O_CREATE
	}
	if flags.Trunc {
		osFlags |= os.O_TRUNC
	}
	if flags.Excl {
		osFlags |= os.O_EXCL
	}
	return os.OpenFile(local, osFlags, h.createMode(r))
}

func (h *Handler) OpenFile(r *sftp.Request) (sftp.WriterAtReaderAt, error) {
	flags := r.Pflags()
	if h.readOnly && (flags.Write || flags.Creat || flags.Trunc) {
		return nil, os.ErrPermission
	}
	local, err := h.mapPath(r.Filepath, true)
	if err != nil {
		return nil, err
	}
	if err := rejectFinalSymlink(local); err != nil {
		return nil, err
	}
	osFlags := unix.O_NOFOLLOW
	switch {
	case flags.Read && flags.Write:
		osFlags |= os.O_RDWR
	case flags.Write:
		osFlags |= os.O_WRONLY
	case flags.Read:
		osFlags |= os.O_RDONLY
	default:
		return nil, os.ErrInvalid
	}
	if flags.Creat {
		osFlags |= os.O_CREATE
	}
	if flags.Trunc {
		osFlags |= os.O_TRUNC
	}
	if flags.Excl {
		osFlags |= os.O_EXCL
	}
	return os.OpenFile(local, osFlags, h.createMode(r))
}

func (h *Handler) Filecmd(r *sftp.Request) error {
	if h.readOnly {
		switch r.Method {
		case "Setstat", "Rename", "Rmdir", "Mkdir", "Link", "Symlink", "Remove", "PosixRename":
			return os.ErrPermission
		}
	}

	switch r.Method {
	case "Setstat":
		local, err := h.mapPath(r.Filepath, false)
		if err != nil {
			return err
		}
		attributes := r.Attributes()
		flags := r.AttrFlags()
		if attributes == nil {
			return nil
		}
		if flags.Size {
			if err := os.Truncate(local, int64(attributes.Size)); err != nil {
				return err
			}
		}
		if flags.Permissions {
			if err := os.Chmod(local, attributes.FileMode()); err != nil {
				return err
			}
		}
		if flags.UidGid {
			if err := os.Chown(local, int(attributes.UID), int(attributes.GID)); err != nil && !errors.Is(err, os.ErrPermission) {
				return err
			}
		}
		if flags.Acmodtime {
			if err := os.Chtimes(local, attributes.AccessTime(), attributes.ModTime()); err != nil {
				return err
			}
		}
		return nil

	case "Rename", "PosixRename":
		oldLocal, err := h.mapPath(r.Filepath, false)
		if err != nil {
			return err
		}
		newLocal, err := h.mapPath(r.Target, false)
		if err != nil {
			return err
		}
		return os.Rename(oldLocal, newLocal)

	case "Rmdir", "Remove":
		local, err := h.mapPath(r.Filepath, false)
		if err != nil {
			return err
		}
		return os.Remove(local)

	case "Mkdir":
		local, err := h.mapPath(r.Filepath, false)
		if err != nil {
			return err
		}
		mode := os.FileMode(0o755)
		if attributes := r.Attributes(); attributes != nil {
			if permissions := attributes.FileMode() & os.ModePerm; permissions != 0 {
				mode = permissions
			}
		}
		return os.Mkdir(local, mode)

	case "Link":
		oldLocal, err := h.mapPath(r.Filepath, false)
		if err != nil {
			return err
		}
		newLocal, err := h.mapPath(r.Target, false)
		if err != nil {
			return err
		}
		return os.Link(oldLocal, newLocal)

	case "Symlink":
		return h.symlink(r.Filepath, r.Target)

	default:
		return os.ErrInvalid
	}
}

func (h *Handler) Filelist(r *sftp.Request) (sftp.ListerAt, error) {
	switch r.Method {
	case "List":
		local, err := h.mapPath(r.Filepath, true)
		if err != nil {
			return nil, err
		}
		entries, err := os.ReadDir(local)
		if err != nil {
			return nil, err
		}
		infos := make(fileInfoLister, 0, len(entries))
		for _, entry := range entries {
			info, err := entry.Info()
			if err != nil {
				return nil, err
			}
			infos = append(infos, info)
		}
		return infos, nil

	case "Stat":
		local, err := h.mapPath(r.Filepath, true)
		if err != nil {
			return nil, err
		}
		info, err := os.Stat(local)
		if err != nil {
			return nil, err
		}
		return fileInfoLister{info}, nil

	case "Lstat":
		local, err := h.mapPath(r.Filepath, false)
		if err != nil {
			return nil, err
		}
		info, err := os.Lstat(local)
		if err != nil {
			return nil, err
		}
		return fileInfoLister{info}, nil

	default:
		return nil, os.ErrInvalid
	}
}

func (h *Handler) Lstat(r *sftp.Request) (sftp.ListerAt, error) {
	return h.Filelist(r)
}

func (h *Handler) Readlink(p string) (string, error) {
	local, err := h.mapPath(p, false)
	if err != nil {
		return "", err
	}
	target, err := os.Readlink(local)
	if err != nil {
		return "", err
	}

	// sshfs resolves absolute link targets on the client side.  Report a
	// relative target rooted at the link so an absolute target such as
	// /etc/passwd is never followed on the client's own filesystem.
	var targetLocal string
	if path.IsAbs(target) {
		targetLocal, err = h.mapPath(target, false)
		if err != nil {
			return "", err
		}
	} else {
		targetLocal = filepath.Join(filepath.Dir(local), filepath.FromSlash(target))
		if !within(h.root, targetLocal) {
			return "", os.ErrPermission
		}
	}

	if resolved, err := filepath.EvalSymlinks(targetLocal); err == nil {
		if !within(h.root, resolved) {
			return "", os.ErrPermission
		}
		targetLocal = resolved
	} else if !errors.Is(err, os.ErrNotExist) {
		return "", err
	}

	relative, err := filepath.Rel(filepath.Dir(local), targetLocal)
	if err != nil {
		return "", err
	}
	return filepath.ToSlash(relative), nil
}

func (h *Handler) RealPath(p string) (string, error) {
	clean := path.Clean("/" + strings.TrimPrefix(p, "/"))
	return clean, nil
}

// StatVFS reports the filesystem that contains the requested path.  sshfs
// asks for this to render free-space information in Dolphin.
func (h *Handler) StatVFS(r *sftp.Request) (*sftp.StatVFS, error) {
	local, err := h.mapPath(r.Filepath, true)
	if err != nil {
		local = h.root
	}
	var stat unix.Statfs_t
	if err := unix.Statfs(local, &stat); err != nil {
		return nil, err
	}
	return &sftp.StatVFS{
		Bsize:   uint64(stat.Bsize),
		Frsize:  uint64(stat.Frsize),
		Blocks:  stat.Blocks,
		Bfree:   stat.Bfree,
		Bavail:  stat.Bavail,
		Files:   stat.Files,
		Ffree:   stat.Ffree,
		Favail:  stat.Ffree,
		Namemax: uint64(stat.Namelen),
	}, nil
}

func (h *Handler) createMode(r *sftp.Request) os.FileMode {
	if attributes := r.Attributes(); attributes != nil {
		if permissions := attributes.FileMode() & os.ModePerm; permissions != 0 {
			return permissions
		}
	}
	return 0o644
}

func (h *Handler) symlink(target, linkPath string) error {
	linkLocal, err := h.mapPath(linkPath, false)
	if err != nil {
		return err
	}

	var targetLocal string
	if path.IsAbs(target) {
		targetLocal, err = h.mapPath(target, false)
		if err != nil {
			return err
		}
	} else {
		targetLocal = filepath.Join(filepath.Dir(linkLocal), filepath.FromSlash(target))
		if !within(h.root, targetLocal) {
			return os.ErrPermission
		}
	}

	relative, err := filepath.Rel(filepath.Dir(linkLocal), targetLocal)
	if err != nil {
		return err
	}
	if !within(h.root, targetLocal) {
		return os.ErrPermission
	}
	return os.Symlink(relative, linkLocal)
}

// mapPath converts a virtual SFTP path to a host path.  When followFinal is
// true, the final component is resolved so symlinks cannot escape the root.
// When it is false, the parent is resolved and the final component is left
// alone, so lstat/readlink/remove operate on the link itself.
func (h *Handler) mapPath(p string, followFinal bool) (string, error) {
	clean := path.Clean("/" + strings.TrimPrefix(p, "/"))
	if clean == "/" {
		return h.root, nil
	}
	relative := strings.TrimPrefix(clean, "/")
	local := filepath.Join(h.root, filepath.FromSlash(relative))
	if !within(h.root, local) {
		return "", os.ErrPermission
	}

	if followFinal {
		resolved, err := filepath.EvalSymlinks(local)
		if err == nil {
			if !within(h.root, resolved) {
				return "", os.ErrPermission
			}
			return resolved, nil
		}
		if !errors.Is(err, os.ErrNotExist) {
			return "", err
		}
	}

	parent := filepath.Dir(local)
	resolvedParent, err := filepath.EvalSymlinks(parent)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			// The operation will report ENOENT; the path itself is still
			// inside the root.
			return local, nil
		}
		return "", err
	}
	if !within(h.root, resolvedParent) {
		return "", os.ErrPermission
	}
	return filepath.Join(resolvedParent, filepath.Base(local)), nil
}

func rejectFinalSymlink(path string) error {
	info, err := os.Lstat(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return os.ErrPermission
	}
	return nil
}

func within(root, candidate string) bool {
	relative, err := filepath.Rel(root, candidate)
	if err != nil {
		return false
	}
	return relative != ".." && !strings.HasPrefix(relative, ".."+string(os.PathSeparator))
}

type fileInfoLister []os.FileInfo

func (l fileInfoLister) ListAt(target []os.FileInfo, offset int64) (int, error) {
	if offset < 0 || offset >= int64(len(l)) {
		return 0, io.EOF
	}
	n := copy(target, l[offset:])
	if n < len(target) {
		return n, io.EOF
	}
	return n, nil
}
