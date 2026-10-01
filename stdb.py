import struct
import os

class XboxSoundtrack:
    def __init__(self, st_id, name):
        self.st_id = st_id
        self.name = name
        self.songs = [] # list of dict: {id, time, name}
        self.total_time = 0

class STDB:
    def __init__(self):
        self.soundtracks = []
        self.next_st_id = 1
        self.next_song_id = 1
    
    def read(self, filepath):
        with open(filepath, 'rb') as f:
            data = f.read()
            
        if len(data) < 512:
            return
            
        magic, num_st, self.next_st_id = struct.unpack('<iii', data[0:12])
        st_ids = struct.unpack('<100i', data[12:412])
        self.next_song_id = struct.unpack('<i', data[412:416])[0]
        
        # The main header contains an array of 100 Soundtrack IDs. 
        # The number of active soundtracks is given by num_st.
        valid_st_ids = st_ids[:num_st]
        
        # Read soundtracks
        st_dict = {}
        for i in range(100):
            offset = 512 + (i * 512)
            st_data = data[offset:offset+512]
            st_magic, st_id, num_songs = struct.unpack('<iii', st_data[0:12])
            
            if st_magic != 0x00021371:
                continue
                
            if st_id not in valid_st_ids:
                continue
                
            group_ids = struct.unpack('<84i', st_data[12:348])
            total_time = struct.unpack('<i', st_data[348:352])[0]
            
            # Wchar string
            name_bytes = st_data[352:480]
            name = name_bytes.decode('utf-16-le').rstrip('\x00')
            
            if st_id not in st_dict:
                st = XboxSoundtrack(st_id, name)
                st.total_time = total_time
                st.group_ids = [gid for gid in group_ids if gid != 0]
                st_dict[st_id] = st
            
        # Read Song Groups
        # Maximum song groups varies, let's just parse until end
        offset = 0xCA00
        while offset + 512 <= len(data):
            sg_data = data[offset:offset+512]
            sg_magic, st_id, sg_id, _pad = struct.unpack('<iiii', sg_data[0:16])
            
            if sg_magic == 0x00031073 and st_id in st_dict:
                song_ids = struct.unpack('<6i', sg_data[16:40])
                song_times = struct.unpack('<6i', sg_data[40:64])
                
                for i in range(6):
                    s_id = song_ids[i]
                    if s_id != 0:
                        s_time = song_times[i]
                        # 64 bytes per name
                        s_name_bytes = sg_data[64+(i*64):64+((i+1)*64)]
                        s_name = s_name_bytes.decode('utf-16-le').rstrip('\x00')
                        st_dict[st_id].songs.append({'id': s_id, 'time': s_time, 'name': s_name})
            offset += 512
            
        # Sort soundtracks to match the order in valid_st_ids and remove duplicates
        self.soundtracks = []
        for sid in valid_st_ids:
            if sid in st_dict:
                self.soundtracks.append(st_dict[sid])
            
    def save(self, filepath):
        # We need to build the file
        main_header = bytearray(512)
        struct.pack_into('<iii', main_header, 0, 0x00000001, len(self.soundtracks), self.next_st_id)
        
        st_ids = [0] * 100
        for i, st in enumerate(self.soundtracks):
            if i < 100:
                st_ids[i] = st.st_id
        struct.pack_into('<100i', main_header, 12, *st_ids)
        struct.pack_into('<i', main_header, 412, self.next_song_id)
        
        with open(filepath, 'wb') as f:
            f.write(main_header)
            
            # Soundtracks
            global_group_counter = 0
            song_groups = []
            
            for i in range(100):
                st_data = bytearray(512)
                if i < len(self.soundtracks):
                    st = self.soundtracks[i]
                    
                    # Split songs into groups of 6
                    groups = []
                    for j in range(0, len(st.songs), 6):
                        groups.append(st.songs[j:j+6])
                    
                    g_ids = [0] * 84
                    for g_idx, g in enumerate(groups):
                        if g_idx < 84:
                            g_ids[g_idx] = global_group_counter
                            song_groups.append((st.st_id, g_idx, g))
                            global_group_counter += 1
                            
                    st_time = sum([s['time'] for s in st.songs])
                    st_name = st.name.encode('utf-16-le').ljust(128, b'\x00')[:128]
                    
                    struct.pack_into('<iii', st_data, 0, 0x00021371, st.st_id, len(st.songs))
                    struct.pack_into('<84i', st_data, 12, *g_ids)
                    struct.pack_into('<i', st_data, 348, st_time)
                    st_data[352:480] = st_name
                f.write(st_data)
                
            # Write song groups
            groups_written = 0
            for (st_id, g_id, group_songs) in song_groups:
                sg_data = bytearray(512)
                # The 4th integer (pad) MUST be 1, which means 'valid/active'. If 0, the Xbox ignores the entire group!
                struct.pack_into('<iiii', sg_data, 0, 0x00031073, st_id, g_id, 1)
                
                s_ids = [0] * 6
                s_times = [0] * 6
                for idx, song in enumerate(group_songs):
                    s_ids[idx] = (st_id << 16) | song['id']
                    s_times[idx] = song['time']
                    
                    s_name = song['name'].encode('utf-16-le').ljust(64, b'\x00')[:64]
                    sg_data[64+(idx*64):64+((idx+1)*64)] = s_name
                    
                struct.pack_into('<6i', sg_data, 16, *s_ids)
                struct.pack_into('<6i', sg_data, 40, *s_times)
                
                f.write(sg_data)
                groups_written += 1
                
            # Xbox dynamically sizes ST.DB, no padding required!

    def add_soundtrack(self, name):
        st = XboxSoundtrack(self.next_st_id, name)
        self.next_st_id += 1
        self.soundtracks.append(st)
        return st

    def add_song(self, st_id, name, time_ms):
        for st in self.soundtracks:
            if st.st_id == st_id:
                song_id = self.next_song_id
                self.next_song_id += 1
                st.songs.append({'id': song_id, 'time': time_ms, 'name': name})
                return song_id
        return None
