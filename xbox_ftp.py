import ftplib
import os
from io import BytesIO

class XboxFTP:
    def __init__(self, ip, user="xbox", passwd="xbox", port=21):
        self.ip = ip
        self.user = user
        self.passwd = passwd
        self.port = port
        self.ftp = None
        self.music_path = None

    def connect(self):
        self.ftp = ftplib.FTP()
        self.ftp.connect(self.ip, self.port, timeout=5)
        self.ftp.login(self.user, self.passwd)
        self._probe_music_path()
        
    def _probe_music_path(self):
        possible_paths = [
            '/HDD0-E/TDATA/fffe0000/music',
            '/E/TDATA/fffe0000/music',
            '/E:/TDATA/fffe0000/music',
            '/e/tdata/fffe0000/music',
            '/Harddisk0/Partition1/TDATA/fffe0000/music',
            'E:/TDATA/fffe0000/music',
            '/E-Drive/TDATA/fffe0000/music',
            '/TDATA/fffe0000/music', # Some FTP servers drop the drive letter
            '/C/TDATA/fffe0000/music', # UIX alpha mounts Scene E as C
            '/c/tdata/fffe0000/music',
            'C:/TDATA/fffe0000/music'
        ]
        for path in possible_paths:
            try:
                self.ftp.cwd(path)
                self.music_path = path
                return
            except ftplib.error_perm:
                continue
        raise Exception("Could not locate the TDATA/fffe0000/music folder on the FTP server.")
        
    def download_stdb(self):
        if not self.music_path:
            return None
        buf = BytesIO()
        try:
            self.ftp.retrbinary(f'RETR {self.music_path}/ST.DB', buf.write)
            buf.seek(0)
            return buf.read()
        except ftplib.error_perm:
            return None

    def upload_stdb(self, data):
        if not self.music_path:
            return
        buf = BytesIO(data)
        self.ftp.storbinary(f'STOR {self.music_path}/ST.DB', buf)
        
    def upload_wma(self, local_path, st_id_str, remote_filename, progress_callback=None):
        if not self.music_path:
            return
        remote_dir = f"{self.music_path}/{st_id_str}"
        try:
            self.ftp.cwd(remote_dir)
        except ftplib.error_perm:
            self.ftp.mkd(remote_dir)
            self.ftp.cwd(remote_dir)
            
        file_size = os.path.getsize(local_path)
        uploaded = 0
        
        def cb(block):
            nonlocal uploaded
            uploaded += len(block)
            if progress_callback:
                progress_callback(uploaded, file_size)
                
        with open(local_path, 'rb') as f:
            self.ftp.storbinary(f'STOR {remote_filename}', f, blocksize=8192, callback=cb)

    def disconnect(self):
        if self.ftp:
            self.ftp.quit()
            self.ftp = None
