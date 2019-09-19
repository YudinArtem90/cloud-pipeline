import io
import logging

from fsclient import FileSystemClient
from fuseutils import MB


class _FileBuffer(object):

    def __init__(self, offset, capacity):
        self._offset = offset
        self._current_offset = self._offset
        self._capacity = capacity
        self._buffs = []

    @property
    def offset(self):
        return self._current_offset

    @property
    def capacity(self):
        return self._capacity

    def append(self, buf, offset=None):
        if offset and offset != self._current_offset:
            raise RuntimeError('Only sequential writes supported. Offset differs %s != %s '
                               % (offset, self._current_offset))
        self._buffs.append(buf)
        self._current_offset += len(buf)


class _WriteBuffer(_FileBuffer):

    def is_full(self):
        return self._current_offset - self._offset >= self._capacity

    def collect(self):
        collected_buf_size = self._current_offset - self._offset
        collected_buf = bytearray(collected_buf_size)
        current_offset = 0
        for current_buf in self._buffs:
            current_buf_size = len(current_buf)
            collected_buf[current_offset:current_offset + current_buf_size] = current_buf
            current_offset += current_buf_size
        return collected_buf, self._offset


class _ReadBuffer(_FileBuffer):

    def view(self, offset, length):
        start = offset
        end = min(start + length, self._capacity)
        second_buf_shift = len(self._buffs[0])
        gap = self._offset + second_buf_shift
        relative_start = start - self._offset
        relative_end = end - self._offset
        if end <= gap:
            return self._buffs[0][relative_start:relative_end]
        elif start >= gap:
            relative_start = relative_start - second_buf_shift
            relative_end = relative_end - second_buf_shift
            return self._buffs[1][relative_start:relative_end]
        else:
            relative_gap = gap - self._offset
            return self._buffs[0][relative_start:relative_gap] \
                   + self._buffs[1][relative_gap - second_buf_shift:relative_end - second_buf_shift]

    def suits(self, offset, length):
        return self._offset <= offset <= self._current_offset and \
               (offset + length <= self._current_offset or self._current_offset == self._capacity)

    def shrink(self):
        if len(self._buffs) > 2:
            old_first_buf = self._buffs.pop(0)
            self._offset += len(old_first_buf)


class BufferedFileSystemClient(FileSystemClient):

    _READ_AHEAD_SIZE = 20 * MB

    def __init__(self, inner, capacity):
        """
        Buffering file system client decorator.

        It merges multiple writes to temporary buffers to reduce number of calls to an inner file system client.

        :param inner: Decorating file system client.
        :param capacity: Capacity of single file buffer in bytes.
        """
        self._inner = inner
        self._capacity = capacity
        self._download_file_buffs = {}
        self._read_file_buffs = {}

    def is_available(self):
        return self._inner.is_available()

    def exists(self, path):
        return self._inner.exists(path)

    def attrs(self, path):
        return self._inner.attrs(path)

    def ls(self, path, depth=1):
        return self._inner.ls(path, depth)

    def upload(self, buf, path):
        self._inner.upload(buf, path)

    def delete(self, path):
        self._inner.delete(path)

    def mv(self, old_path, path):
        self._inner.mv(old_path, path)

    def mkdir(self, path):
        self._inner.mkdir(path)

    def rmdir(self, path):
        self._inner.rmdir(path)

    def download_range(self, fd, buf, path, offset=0, length=0):
        buf_key = fd, path
        file_buf = self._read_file_buffs.get(buf_key)
        if not file_buf:
            file_size = self.attrs(path).size
            if not file_size:
                return
            file_buf = self._new_read_buf(fd, path, file_size, offset)
            self._read_file_buffs[buf_key] = file_buf
        if not file_buf.suits(offset, length):
            file_buf.append(self._read_ahead(fd, path, file_buf.offset))
            file_buf.shrink()
            if not file_buf.suits(offset, length):
                file_buf = self._new_read_buf(fd, path, file_buf.capacity, offset)
                self._read_file_buffs[buf_key] = file_buf
        buf.write(file_buf.view(offset, length))

    def _new_read_buf(self, fd, path, file_size, offset):
        file_buf = _ReadBuffer(offset, file_size)
        file_buf.append(self._read_ahead(fd, path, offset))
        return file_buf

    def _read_ahead(self, fd, path, offset):
        with io.BytesIO() as read_ahead_buf:
            self._inner.download_range(fd, read_ahead_buf, path, offset, length=self._READ_AHEAD_SIZE)
            return read_ahead_buf.getvalue()

    def upload_range(self, fd, buf, path, offset=0):
        buf_key = fd, path
        file_buf = self._download_file_buffs.get(buf_key)
        if not file_buf:
            file_buf = _WriteBuffer(offset, self._capacity)
            self._download_file_buffs[buf_key] = file_buf
        file_buf.append(buf, offset)
        if file_buf.is_full():
            logging.info('Uploading buffer is full for %d:%s. Buffer will be cleared.' % (fd, path))
            write_buf = self._download_file_buffs.pop(buf_key, None)
            if write_buf:
                collected_buf, collected_offset = write_buf.collect()
                self._inner.upload_range(fd, collected_buf, path, collected_offset)

    def flush(self, fd, path):
        buf_key = fd, path
        self._read_file_buffs.pop(buf_key, None)
        write_buf = self._download_file_buffs.pop(buf_key, None)
        logging.info('Flushing buffers for %d:%s' % (fd, path))
        if write_buf:
            buf, offset = write_buf.collect()
            self._inner.upload_range(fd, buf, path, offset)
        self._inner.flush(fd, path)

    def __getattr__(self, name):
        if hasattr(self._inner, name):
            return getattr(self._inner, name)
        else:
            raise RuntimeError('BufferedFileSystemClient or its inner client doesn\'t have %s attribute.' % name)
