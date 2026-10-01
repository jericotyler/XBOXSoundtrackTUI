import os
import tempfile
import json
from pathlib import Path
from textual.app import App, ComposeResult
from textual import work
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical, VerticalScroll, Grid
from textual.widgets import Header, Select, Footer, DirectoryTree, Button, Static, Input, Tree, Label, Log, TabbedContent, TabPane, ProgressBar, ListView, ListItem, Checkbox
from textual.binding import Binding
from rich.text import Text
from rich.markup import escape

from stdb import STDB
from converter import convert_to_wma
from xbox_ftp import XboxFTP
from tinytag import TinyTag

CONFIG_DIR = os.path.join(Path.home( ), ".config", "xbox-soundtrack-manager")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"ip": "192.168.1.100", "port": 21, "user": "xbox", "pass": "xbox", "music_dir": "~/Music"}

def save_config(ip, port, user, passwd, music_dir, backup_dir="~/XboxSoundtrackBackups"):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump({"ip": ip, "port": port, "user": user, "pass": passwd, "music_dir": music_dir, "backup_dir": backup_dir}, f)
    except:
        pass


class WipeConfirmScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Vertical(id="wipe_dialog"):
            yield Label("ARE YOU SURE?", id="wipe_title")
            yield Label("This will permanently delete the ST.DB and ALL custom soundtracks from your Xbox.", id="wipe_desc")
            yield Checkbox("I understand this cannot be undone.", id="wipe_check")
            with Horizontal( ):
                yield Button("Cancel", variant="primary", id="wipe_cancel")
                yield Button("WIPE XBOX", variant="error", id="wipe_yes", disabled=True)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "wipe_check":
            self.query_one("#wipe_yes", Button).disabled = not event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "wipe_yes":
            self.dismiss(True)
        elif event.button.id == "wipe_cancel":
            self.dismiss(False)

class XboxSoundtrackTUI(App):
    CSS = """










    #wipe_dialog Button {
        width: 1fr;
        margin: 0 1;
        height: 3;
        padding: 0;
    }
    WipeConfirmScreen {
        align: center middle;
        background: $background 50%;
    }
    #wipe_dialog {
        layout: vertical;
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $error;
        background: $surface;
    }
    #wipe_dialog Horizontal {
        height: auto;
    }
    #wipe_check {
        margin: 1 0;
    }
    #wipe_title {
        content-align: center middle;
        text-style: bold;
        color: $error;
    }
    #wipe_desc {
        content-align: center middle;
    }
    #credits_text {
        content-align: center middle;
        height: 100%;
        margin: 2;
    }
    #main-layout {
        height: 1fr;
        layout: horizontal;
    }
    .panel {
        width: 1fr;
        height: 1fr;
        border: solid green;
        padding: 1;
    }
    #middle-panel {
        width: 1fr;
        height: 1fr;
        border: solid blue;
        padding: 1;
    }
    #credentials {
        height: 3;
        layout: horizontal;
    }
    #credentials Input {
        width: 1fr;
    }
    .settings-panel {
        width: 1fr;
        height: auto;
        padding: 2;
    }
    .settings-panel Input {
        margin-bottom: 1;
    }
    Log {
        height: 10;
        border: solid red;
    }

    #queue_list {
        height: 1fr;
        min-height: 5;
        border: solid yellow;
        padding: 0;
    }
    .instruction-text {
        text-style: italic;
        color: $text-muted;
        height: auto;
        width: 100%;
    }
    .settings-panel Horizontal, .settings-panel Vertical {
        height: auto;
    }
    .mixtape-controls {
        height: auto;
    }
    .mixtape-controls Button {
        width: 1fr;
        margin-right: 1;
    }














































    



    
















    



    
















    





    
















    





    

    

    

    

    

    

    

    


    

    

    



    Button {
        min-height: 1;
        height: auto;
        border: none;
        padding: 0 1;
        margin: 1 1;
    }
    
    .big-btn {
        height: 3;
        border: none;
        padding: 1 4;
        margin: 1 2;
    }
    
    /* Overrides for Connect and Sync to be thin */





    #btn_db_refresh_backups {
        min-height: 1;
        height: 3;
        margin: 0;
        border: none;
        padding: 1 2;
    }
    
    .db-controls {
        height: auto;
    }
    

    

    
    .spacer {
        height: 1fr;
    }
    
    #db_main_panel {
        height: 1fr;
        min-height: 10;
        padding: 0 1 0 1;
        margin-top: 0;
    }
    
    .db-lists {
        height: 1fr;
        width: 1fr;
    }
    
    .db-list-wrapper {
        width: 1fr;
        height: 1fr;
    }
    
    .db-backup-panel {
        height: auto;
    }
    .db-backup-panel .panel {
        height: auto;
        width: 1fr;
    }
    
    #db_st_list, #db_song_list {
        height: 1fr;
        border: solid $accent;
    }
    
    #select_backup {
        width: 1fr;
    }
    
    .wipe-panel {
        border: solid red;
        padding: 1;
        margin-top: 0;
        height: auto;
        align: center middle;
    }
    .wipe-panel Label, .wipe-panel Checkbox {
        content-align: center middle;
    }

    .db-actions-col {
        width: 5;
        height: 1fr;
        padding-left: 0;
        margin-left: 1;
    }
    


    #btn_db_connect {
        width: 100%;
        height: 1;
        border: none;
        margin: 0;
    }
    #top-connect-bar {
        height: auto;
        margin-bottom: 0;
        padding-bottom: 0;
    }

    #btn_db_sync {
        margin: 0;
        padding: 0;
        height: 1;
        width: 100%;
        border: none;
    }

    .db-actions-col Button {
        width: 5;
        min-width: 3;
        height: 3;
        border: none;
        padding: 0;
        margin: 0 0 1 0;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "rescan", "Rescan Library", show=True),
    ]

    def __init__(self):
        super( ).__init__( )
        self.stdb = STDB( )
        self.ftp = None
        config = load_config( )
        self.music_dir = os.path.expanduser(config.get("music_dir", "~/Music"))
        self.library_data = {}
        self.selected_album = None
        self.album_queue = []
        self.mixtape_tracks = []
        self.mixtape_selected_song = None
        self.is_processing = False
        self.db_pending_st_deletes = set()
        self.db_pending_song_deletes = set()
        self.db_song_order = {}
        
    def compose(self) -> ComposeResult:
        config = load_config( )
        yield Header(show_clock=True)
        with TabbedContent( ):
            with TabPane("Albums", id="tab_main"):
                with Horizontal(id="main-layout"):
                    with Vertical(classes="panel"):
                        yield Label("Local Library", classes="panel-title")
                        tree = Tree("Library", id="library_tree")
                        tree.auto_expand = False
                        tree.root.expand()
                        yield tree
                        yield Button("Queue Selected Items", id="btn_queue", disabled=True, variant="primary")
                    
                    with VerticalScroll(id="middle-panel"):
                        yield Label("Process Guide", classes="panel-title")
                        yield Label("1. Connect and sync DB.", classes="instruction-text")
                        yield Label("2. Select an album from the local library (individual tracks can be selected and deselected).", classes="instruction-text")
                        yield Label("3. Once all albums have been selected, click queue selected items.", classes="instruction-text")
                        yield Label("4. Once the queue is complete, click start uploading queue.", classes="instruction-text")
                        yield Label(" ")
                        yield Label("Upload Queue:")
                        yield ListView(id="queue_list")
                        yield Button("Start Uploading Queue", id="btn_start_queue", disabled=True, variant="warning")
                        yield Label(" ")
                        yield Label("Overall Queue Progress:")
                        yield ProgressBar(id="prog_queue", show_eta=False)
                        yield Label("Current Album Progress:")
                        yield ProgressBar(id="prog_album", show_eta=False)
                        yield Label("Current File Conversion:")
                        yield ProgressBar(id="prog_convert", show_eta=False)
                        yield Label("Current File Upload:")
                        yield ProgressBar(id="prog_upload", show_eta=False)
                        yield Label(" ")
                        yield Label("Status Log")
                        yield Log(id="status_log")
                        
                    with Vertical(classes="panel"):
                        yield Label("Xbox Soundtracks", classes="panel-title")
                        yield Button("Connect & Sync DB", id="btn_connect", variant="success")
                        yield Label(" ")
                        st_tree = Tree("Soundtracks", id="xbox_soundtracks_tree")
                        st_tree.root.expand( )
                        yield st_tree
            with TabPane("Mixtape", id="tab_mixtape"):
                with Horizontal():
                    with Vertical(classes="panel"):
                        yield Label("Local Library", classes="panel-title")
                        mix_tree = Tree("Library", id="mixtape_tree")
                        mix_tree.root.expand()
                        yield mix_tree
                        yield Label("Selected: None", id="mix_selected_lbl")
                        yield Button("Add to List", id="btn_mix_add", disabled=True, variant="primary")
                    with VerticalScroll(classes="panel", id="middle-panel"):
                        yield Label("Mixtape Name:", classes="panel-title")
                        yield Input(id="mixtape_name", placeholder="e.g. Tony Hawk Pro Skater")
                        yield Label("Track List:", classes="panel-title")
                        yield ListView(id="mixtape_list")
                        with Horizontal(classes="mixtape-controls"):
                            yield Button("↑ Up", id="btn_mix_up")
                            yield Button("↓ Down", id="btn_mix_down")
                            yield Button("Delete", id="btn_mix_remove", variant="error")
                        yield Label(" ")
                        yield Button("Queue & Start Upload", id="btn_mix_start", variant="warning")
                        yield Label(" ")
                        yield Label("Upload Queue:", classes="panel-title")
                        yield ListView(id="mix_queue_list")
                        yield Label("Overall Progress:")
                        yield ProgressBar(id="prog_mix_queue", show_eta=False)
                        yield Label("Track Progress:")
                        yield ProgressBar(id="prog_mix_track", show_eta=False)
                    with Vertical(classes="panel"):
                        yield Label("Xbox Soundtracks", classes="panel-title")
                        yield Button("Connect & Sync DB", id="btn_mix_connect", variant="success")
                        yield Label(" ")
                        mx_tree = Tree("Soundtracks", id="mix_xbox_tree")
                        mx_tree.root.expand()
                        yield mx_tree
            
            with TabPane("DB Manager", id="tab_db"):
                from textual.containers import Center
                yield Button("Connect and Sync Database", id="btn_db_connect", variant="success")
                with Vertical(classes="panel", id="db_main_panel"):
                    with Horizontal():
                        with Horizontal(classes="db-lists"):
                            with Vertical(classes="db-list-wrapper"):
                                yield Center(Label("Xbox Soundtracks", classes="panel-title"))
                                yield ListView(id="db_st_list")
                            with Vertical(classes="db-actions-col"):
                                yield Label(" ", classes="spacer")
                                yield Button("X", id="btn_db_st_del", variant="error")
                        yield Label("  ") # Add spacing between the two halves
                        with Horizontal(classes="db-lists"):
                            with Vertical(classes="db-list-wrapper"):
                                yield Center(Label("Tracks", classes="panel-title"))
                                yield ListView(id="db_song_list")
                            with Vertical(classes="db-actions-col"):
                                yield Label(" ", classes="spacer")
                                yield Button("▲", id="btn_db_song_up")
                                yield Button("▼", id="btn_db_song_down")
                                yield Label(" ", classes="spacer")
                                yield Button("X", id="btn_db_song_del", variant="error")
                    yield Button("Sync Changes", id="btn_db_sync", variant="warning", disabled=True)
                with Horizontal(classes="db-backup-panel"):
                    with Vertical(classes="panel"):
                        yield Center(Label("Backup DB & Audio", classes="panel-title"))
                        yield Input(id="input_backup_name", placeholder="Optional Backup Name (e.g. MyBackup)")
                        yield Center(Button("Create ZIP Backup", id="btn_backup", variant="primary", classes="big-btn"))
                        yield Center(Label("Backup Progress:"))
                        yield Center(ProgressBar(id="prog_backup", show_eta=False))
                    with Vertical(classes="panel"):
                        yield Center(Label("Restore Backup", classes="panel-title"))
                        with Horizontal(classes="db-controls"):
                            yield Select([], id="select_backup", prompt="Select a backup...")
                            yield Button("Refresh", id="btn_db_refresh_backups")
                        yield Center(Button("Restore Selected Backup", id="btn_restore", variant="warning", classes="big-btn"))
                        yield Center(Label("Restore Progress:"))
                        yield Center(ProgressBar(id="prog_restore", show_eta=False))
                with Vertical(classes="wipe-panel"):
                    yield Center(Label("Wipe Entire Database (Danger!)", classes="panel-title"))
                    yield Center(Checkbox("I understand these options can destroy my database.", id="chk_wipe_enable"))
                    yield Center(Button("Wipe Xbox Database", id="btn_wipe_db", variant="error", disabled=True, classes="big-btn"))
            with TabPane("Settings", id="tab_settings"):
                with VerticalScroll(classes="settings-panel"):
                    with Horizontal( ):
                        with Vertical( ):
                            yield Label("Xbox IP Address:")
                            yield Input(id="set_ip", value=config.get("ip", "192.168.1.100"))
                        with Vertical( ):
                            yield Label("FTP Port:")
                            yield Input(id="set_port", value=str(config.get("port", "21")))
                    with Horizontal( ):
                        with Vertical( ):
                            yield Label("FTP Username:")
                            yield Input(id="set_user", value=config.get("user", "xbox"))
                        with Vertical( ):
                            yield Label("FTP Password:")
                            yield Input(id="set_pass", value=config.get("pass", "xbox"), password=True)
                    yield Label("Local Music Directory:")
                    yield Input(id="set_music_dir", value=config.get("music_dir", "~/Music"))
                    yield Label("Backup Location:")
                    yield Input(id="set_backup_dir", value=config.get("backup_dir", "~/XboxSoundtrackBackups"))
                    yield Label(" ")
                    yield Button("Save & Apply Settings", id="btn_save_settings", variant="primary")
            with TabPane("Credits", id="tab_credits"):
                with VerticalScroll(classes="panel"):
                    yield Static(
                        "[b]Xbox Soundtrack TUI[/b]\n\n"
                        "This application was coded by Gemini on Antigravity with the guidance of a human.\n\n""[i]\"I needed an app that would actually work on linux to make/transfer/manage soundtracks on my orginal xbox and didn't have the skill to do it myself. I provide this tool to the community as is with the hope it could be ported or remade for all systems\"[/i] - Hirschmark\n\n"
                        "[b]Core Dependencies:[/b]\n"
                        "- [b]Textual[/b]: Terminal user interface framework\n"
                        "- [b]TinyTag[/b]: Audio metadata and duration extraction\n"
                        "- [b]FFmpeg[/b]: Audio conversion and resampling to 16-bit 44.1kHz WMA\n"
                        "- [b]Python Standard Library[/b]: FTPlib, Struct, OS, Tempfile\n\n"
                        "[b]Special Thanks & References:[/b]\n"
                        "- [b]XboxDevWiki & Community[/b]: Reference material for Xbox file formats.\n"
                        "- [b]ST.DB Parser[/b]: The internal ST.DB database structure was reverse-engineered from scratch via hex-editing.\n", 
                        markup=True, id="credits_text"
                    )
        yield Footer( )

    def on_mount(self) -> None:
        self.log_msg("Scanning local music library...")
        try:
            self.action_db_refresh_backups()
        except Exception:
            pass
        self._scan_library( )

    def action_rescan(self) -> None:
        self.log_msg("Rescanning local music library...")
        try:
            self.action_db_refresh_backups()
        except Exception:
            pass
        self._scan_library( )

    @work(thread=True)
    def _scan_library(self):
        valid_exts = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', '.wma'}
        library = {}
        
        for root, _, files in os.walk(self.music_dir):
            for file in files:
                path = Path(root) / file
                if path.suffix.lower( ) in valid_exts:
                    try:
                        tag = TinyTag.get(str(path))
                        
                        # Prioritize albumartist to group albums correctly, fallback to artist
                        if tag.albumartist:
                            artist = tag.albumartist
                        elif tag.artist:
                            artist = tag.artist
                        else:
                            artist = "Unknown Artist"
                            
                        album = tag.album if tag.album else "Unknown Album"
                        title = tag.title if tag.title else path.stem
                        track = tag.track if tag.track else 0
                        
                        if artist not in library:
                            library[artist] = {}
                        if album not in library[artist]:
                            library[artist][album] = []
                            
                        library[artist][album].append({
                            "path": str(path),
                            "title": title,
                            "track": track
                        })
                    except:
                        pass
        
        # Sort tracks in albums
        def safe_track_num(val):
            try:
                # Handle "1", "01", "1/10"
                return int(str(val).split('/')[0])
            except:
                return 0
                
        for artist, albums in library.items():
            for album, tracks in albums.items():
                tracks.sort(key=lambda x: (safe_track_num(x.get("track", 0)), x.get("title", "")))
                
        self.library_data = library
        self.call_from_thread(self._populate_library_tree)

    def get_track_status(self, artist, album, title) -> str:
        st_name = f"{artist} - {album}" if artist != "Music" else album
        for st in self.stdb.soundtracks:
            if st.name == st_name[:64]:
                for song in st.songs:
                    if song['name'] == title[:32]:
                        return "xbox"
        for item in self.album_queue:
            if not item.get("is_mixtape"):
                if item["st_name"] == st_name:
                    for t in item["tracks"]:
                        if t["title"] == title:
                            return "queued"
        return "none"

    def format_node_label(self, data) -> Text:
        color_map = {"xbox": "#00ff00", "queued": "#ffff00", "none": ""}
        
        if data["type"] == "song":
            status = self.get_track_status(data["artist"], data["album"], data["track_data"]["title"])
            color = color_map[status]
            chk = "(x)" if data.get("checked") else "( )"
            title = escape(data['track_data']['title'])
            if color:
                return Text.from_markup(f"[{color}]{chk} {title}[/{color}]")
            return Text(f"{chk} {data['track_data']['title']}")
            
        elif data["type"] == "album":
            st_name = data["st_name"]
            is_uploaded = any(st.name == st_name[:64] for st in self.stdb.soundtracks)
            is_queued = any(item["st_name"] == st_name and not item.get("is_mixtape") for item in self.album_queue)
            
            if is_uploaded:
                color = "#00ff00"
            elif is_queued:
                color = "#ffff00"
            else:
                color = ""
                
            chk = "(x)" if data.get("checked") else "( )"
            label = escape(data['original_label'])
            if color:
                return Text.from_markup(f"[{color}]{chk} {label}[/{color}]")
            return Text(f"{chk} {data['original_label']}")

    def _update_tree_labels(self):
        tree = self.query_one("#library_tree", Tree)
        def traverse(node):
            if node.data and "type" in node.data:
                if node.data["type"] in ("song", "album"):
                    node.label = self.format_node_label(node.data)
            for child in node.children:
                traverse(child)
        traverse(tree.root)

    def _populate_library_tree(self):
        tree = self.query_one("#library_tree", Tree)
        tree.clear()
        tree.root.label = str(self.music_dir)
        
        mix_tree = self.query_one("#mixtape_tree", Tree)
        mix_tree.clear()
        mix_tree.root.label = str(self.music_dir)
        
        for artist in sorted(self.library_data.keys()):
            artist_node = tree.root.add(artist, data={"type": "artist"})
            mix_artist_node = mix_tree.root.add(artist, data={"type": "artist"})
            for album, tracks in sorted(self.library_data[artist].items()):
                st_name = f"{artist} - {album}" if artist != "Music" else album
                
                album_label = f"{album} ({len(tracks)} songs)"
                album_data = {"type": "album", "artist": artist, "album": album, "checked": False, "st_name": st_name, "original_label": album_label}
                
                album_node = artist_node.add(self.format_node_label(album_data), data=album_data)
                mix_album_node = mix_artist_node.add(escape(album_label), data=dict(album_data))
                
                for t in tracks:
                    song_data = {"type": "song", "track_data": t, "checked": False, "artist": artist, "album": album, "st_name": st_name}
                    album_node.add_leaf(self.format_node_label(song_data), data=song_data)
                    mix_album_node.add_leaf(escape(t['title']), data=dict(song_data))
                    
        self.log_msg("Library tree updated.")

    def log_msg(self, message: str) -> None:
        self.query_one("#status_log", Log).write_line(message)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "chk_wipe_enable":
            try:
                self.query_one("#btn_wipe_db", Button).disabled = not event.value
            except Exception:
                pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id in ("btn_connect", "btn_mix_connect"):
            self.action_connect( )
        elif btn_id == "btn_queue":
            self.action_queue_album( )
        elif btn_id == "btn_start_queue":
            self.action_start_queue( )
        elif btn_id == "btn_save_settings":
            self.action_save_settings()
        elif btn_id == "btn_wipe_db":
            self.action_wipe_db()
        elif btn_id == "btn_backup":
            self.action_backup()
        elif btn_id == "btn_mix_add":
            self.action_mix_add()
        elif btn_id == "btn_mix_up":
            self.action_mix_up()
        elif btn_id == "btn_mix_down":
            self.action_mix_down()
        elif btn_id == "btn_mix_remove":
            self.action_mix_remove()
        elif btn_id == "btn_mix_start":
            self.action_mix_queue()
        elif btn_id == "btn_db_connect":
            self.action_connect()
        elif btn_id == "btn_db_st_del":
            self.action_db_st_del()
        elif btn_id == "btn_db_song_up":
            self.action_db_song_up()
        elif btn_id == "btn_db_song_down":
            self.action_db_song_down()
        elif btn_id == "btn_db_song_del":
            self.action_db_song_del()
        elif btn_id == "btn_db_sync":
            self.action_db_sync()
        elif btn_id == "btn_db_refresh_backups":
            self.action_db_refresh_backups()
        elif btn_id == "btn_restore":
            self.action_restore()

    def action_wipe_db(self) -> None:
        if not self.ftp:
            self.log_msg("Cannot wipe: Not connected to Xbox.")
            return
            
        def check_wipe(do_wipe: bool):
            if do_wipe:
                self.log_msg("Wiping entire ST.DB and all WMA files on Xbox. This may take a minute...")
                self.stdb = STDB( ) # Blank STDB
                self.refresh_st_list( )
                self._populate_library_tree( )
                self._wipe_xbox_task( )
        self.push_screen(WipeConfirmScreen( ), check_wipe)

    @work(thread=True)
    def _wipe_xbox_task(self):
        try:
            self.ftp.ftp.cwd(self.ftp.music_path)
            items = self.ftp.ftp.nlst( )
            for item in items:
                if item == 'ST.DB':
                    self.ftp.ftp.delete(item)
                elif '.' not in item:
                    self.ftp.ftp.cwd(item)
                    files = self.ftp.ftp.nlst( )
                    for f in files:
                        if f in ['.', '..']: continue
                        self.ftp.ftp.delete(f)
                    self.ftp.ftp.cwd('..')
                    self.ftp.ftp.rmd(item)
            self.call_from_thread(self.log_msg, "Xbox wiped successfully!")
            self.save_and_upload_stdb( )
        except Exception as e:
            self.call_from_thread(self.log_msg, f"Wipe failed: {e}")

    def action_backup(self) -> None:
        if not self.ftp:
            self.log_msg("Cannot backup: Not connected to Xbox.")
            return
        
        config = load_config( )
        backup_dir = os.path.expanduser(config.get("backup_dir", "~/XboxSoundtrackBackups"))
        os.makedirs(backup_dir, exist_ok=True)
        
        self.log_msg(f"Starting backup to {backup_dir}...")
        self.query_one("#btn_backup", Button).disabled = True
        self._backup_task(backup_dir)

    @work(thread=True)
    def _backup_task(self, backup_dir: str):
        try:
            prog = self.query_one("#prog_backup", ProgressBar)
            self.call_from_thread(lambda: prog.update(total=None))
            
            # Download ST.DB
            stdb_local = os.path.join(backup_dir, "ST.DB")
            self.call_from_thread(self.log_msg, "Downloading ST.DB...")
            with open(stdb_local, 'wb') as f:
                self.ftp.ftp.retrbinary(f"RETR {self.ftp.music_path}/ST.DB", f.write)
            
            # Download all folders
            self.ftp.ftp.cwd(self.ftp.music_path)
            folders = self.ftp.ftp.nlst()
            
            audio_files = []
            for item in folders:
                folder_name = os.path.basename(item)
                if folder_name.isdigit( ): # 0000, 0001, etc
                    remote_folder = f"{self.ftp.music_path}/{folder_name}"
                    local_folder = os.path.join(backup_dir, folder_name)
                    os.makedirs(local_folder, exist_ok=True)
                    
                    try:
                        self.ftp.ftp.cwd(remote_folder)
                        files = self.ftp.ftp.nlst()
                        for f in files:
                            remote_file = f"{remote_folder}/{os.path.basename(f)}"
                            local_file = os.path.join(local_folder, os.path.basename(f))
                            audio_files.append((remote_file, local_file))
                    except Exception:
                        pass
            self.ftp.ftp.cwd(self.ftp.music_path)
            total_files = len(audio_files)
            if total_files > 0:
                self.call_from_thread(lambda: prog.update(total=total_files, progress=0))
                for i, (remote, local) in enumerate(audio_files):
                    self.call_from_thread(self.log_msg, f"Backing up [{i+1}/{total_files}]: {os.path.basename(remote)}")
                    with open(local, 'wb') as f:
                        self.ftp.ftp.retrbinary(f"RETR {remote}", f.write)
                    self.call_from_thread(lambda: prog.advance(1))
            
            self.call_from_thread(self.log_msg, "Backup completely successfully!")
        except Exception as e:
            self.call_from_thread(self.log_msg, f"Backup error: {e}")
        finally:
            self.call_from_thread(lambda: prog.update(total=100, progress=100))
            self.call_from_thread(lambda: setattr(self.query_one("#btn_backup", Button), 'disabled', False))

    @work(thread=True)
    def _sync_stdb_task(self):
        self.save_and_upload_stdb( )

    def action_save_settings(self) -> None:
        ip = self.query_one("#set_ip", Input).value
        try:
            port = int(self.query_one("#set_port", Input).value)
        except ValueError:
            port = 21
        user = self.query_one("#set_user", Input).value
        passwd = self.query_one("#set_pass", Input).value
        music_dir = self.query_one("#set_music_dir", Input).value
        backup_dir = self.query_one("#set_backup_dir", Input).value
        
        save_config(ip, port, user, passwd, music_dir, backup_dir)
        self.music_dir = os.path.expanduser(music_dir)
        self.log_msg(f"Settings saved. Library dir updated. Rescanning...")
        try:
            self.action_db_refresh_backups()
        except Exception:
            pass
        self._scan_library( )

    def action_connect(self) -> None:
        ip = self.query_one("#set_ip", Input).value
        user = self.query_one("#set_user", Input).value
        passwd = self.query_one("#set_pass", Input).value
        try:
            port = int(self.query_one("#set_port", Input).value)
        except ValueError:
            port = 21
        
        save_config(ip, port, user, passwd, self.query_one("#set_music_dir", Input).value)
        self.log_msg(f"Connecting to {ip}:{port} as {user}...")
        self._connect_task(ip, port, user, passwd)

    @work(thread=True)
    def _connect_task(self, ip, port, user, passwd):
        self.ftp = XboxFTP(ip, user, passwd, port)
        try:
            self.ftp.connect( )
            self.call_from_thread(self.log_msg, "Connected via FTP! Downloading ST.DB...")
            stdb_data = self.ftp.download_stdb( )
            
            if stdb_data:
                fd, path = tempfile.mkstemp( )
                with os.fdopen(fd, 'wb') as f:
                    f.write(stdb_data)
                
                self.stdb = STDB( )
                self.stdb.read(path)
                os.unlink(path)
                self.call_from_thread(self.log_msg, f"Loaded {len(self.stdb.soundtracks)} soundtracks.")
                
                self.call_from_thread(self.refresh_st_list)
                self.call_from_thread(self._populate_library_tree)
            else:
                self.call_from_thread(self.log_msg, "CRITICAL ERROR: ST.DB not found. Check FTP path. Aborting.")
            
        except Exception as e:
            self.call_from_thread(self.log_msg, f"Connection error: {e}")

    def refresh_st_list(self) -> None:
        tree = self.query_one("#xbox_soundtracks_tree", Tree)
        mix_tree = self.query_one("#mix_xbox_tree", Tree)
        tree.clear()
        mix_tree.clear()
        
        for st in self.stdb.soundtracks:
            # Tree
            st_node = tree.root.add(f"[{st.st_id:04d}] {st.name} ({len(st.songs)} songs)")
            mix_st_node = mix_tree.root.add(f"[{st.st_id:04d}] {st.name} ({len(st.songs)} songs)")
            for song in st.songs:
                # convert ms to m:ss
                mins = song['time'] // 60000
                secs = (song['time'] % 60000) // 1000
                st_node.add_leaf(f"{song['name']} ({mins}:{secs:02d})")
                mix_st_node.add_leaf(f"{song['name']} ({mins}:{secs:02d})")
            
        tree.root.expand()
        mix_tree.root.expand()
        self._update_tree_labels()
        try:
            self.refresh_db_manager_st_list()
        except Exception:
            pass

    def save_and_upload_stdb(self) -> None:
        fd, path = tempfile.mkstemp( )
        os.close(fd)
        try:
            self.stdb.save(path)
            with open(path, 'rb') as f:
                data = f.read( )
            self.ftp.upload_stdb(data)
            self.call_from_thread(self.log_msg, "Saved and synced ST.DB to Xbox.")
        except Exception as e:
            self.call_from_thread(self.log_msg, f"Error saving ST.DB: {e}")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.control.id == "library_tree":
            node = event.node
            data = node.data
            if data and "checked" in data:
                # Toggle state
                data["checked"] = not data["checked"]
                
                # Update text
                node.label = self.format_node_label(data)
                
                # If album, toggle all songs inside it
                if data["type"] == "album":
                    for child in node.children:
                        if child.data and "checked" in child.data:
                            child.data["checked"] = data["checked"]
                            child.label = self.format_node_label(child.data)
                
                if self.ftp:
                    self.query_one("#btn_queue", Button).disabled = False
        elif event.control.id == "mixtape_tree":
            node = event.node
            data = node.data
            if data and data.get("type") == "song":
                self.mixtape_selected_song = dict(data["track_data"])
                self.mixtape_selected_song["artist"] = data.get("artist", "Unknown Artist")
                self.mixtape_selected_song["album"] = data.get("album", "Unknown Album")
                self.query_one("#mix_selected_lbl", Label).update(f"Selected: {self.mixtape_selected_song['artist']} - {self.mixtape_selected_song['title']}")
                self.query_one("#btn_mix_add", Button).disabled = False

    def action_mix_add(self) -> None:
        if self.mixtape_selected_song:
            self.mixtape_tracks.append(self.mixtape_selected_song)
            self._refresh_mixtape_list()
            self.log_msg(f"Added {self.mixtape_selected_song['title']} to mixtape.")

    def _refresh_mixtape_list(self, selected_idx=None) -> None:
        lv = self.query_one("#mixtape_list", ListView)
        lv.clear()
        for i, t in enumerate(self.mixtape_tracks):
            lv.append(ListItem(Label(f"{i+1}. {t['artist']} - {t['title']}")))
        if selected_idx is not None and len(self.mixtape_tracks) > 0:
            lv.index = selected_idx

    def action_mix_up(self) -> None:
        lv = self.query_one("#mixtape_list", ListView)
        idx = lv.index
        if idx is not None and idx > 0:
            self.mixtape_tracks[idx], self.mixtape_tracks[idx-1] = self.mixtape_tracks[idx-1], self.mixtape_tracks[idx]
            self._refresh_mixtape_list()
            lv.index = idx - 1
            lv.focus()

    def action_mix_down(self) -> None:
        lv = self.query_one("#mixtape_list", ListView)
        idx = lv.index
        if idx is not None and idx < len(self.mixtape_tracks) - 1:
            # swap backend
            self.mixtape_tracks[idx], self.mixtape_tracks[idx+1] = self.mixtape_tracks[idx+1], self.mixtape_tracks[idx]
            # swap UI labels directly
            lbl_a = f"{idx+1}. {self.mixtape_tracks[idx]['artist']} - {self.mixtape_tracks[idx]['title']}"
            lbl_b = f"{idx+2}. {self.mixtape_tracks[idx+1]['artist']} - {self.mixtape_tracks[idx+1]['title']}"
            lv.children[idx].query_one(Label).update(lbl_a)
            lv.children[idx+1].query_one(Label).update(lbl_b)
            lv.index = idx + 1
            lv.focus()

    def action_mix_remove(self) -> None:
        lv = self.query_one("#mixtape_list", ListView)
        idx = lv.index
        if idx is not None and 0 <= idx < len(self.mixtape_tracks):
            self.mixtape_tracks.pop(idx)
            new_idx = min(idx, len(self.mixtape_tracks) - 1)
            self._refresh_mixtape_list(selected_idx=new_idx if new_idx >= 0 else None)
            lv.focus()

    def action_mix_queue(self) -> None:
        if not self.mixtape_tracks:
            self.log_msg("Mixtape is empty!")
            return
            
        st_name = self.query_one("#mixtape_name", Input).value.strip()
        if not st_name:
            self.log_msg("Error: Please provide a name for the mixtape.")
            return
            
        # Add to main queue with updated titles
        formatted_tracks = []
        for t in self.mixtape_tracks:
            new_t = dict(t)
            new_t['title'] = f"{t['artist']} - {t['title']}"
            formatted_tracks.append(new_t)
            
        self.album_queue.append({"st_name": st_name, "tracks": formatted_tracks, "is_mixtape": True})
        
        queue_list = self.query_one("#queue_list", ListView)
        queue_list.append(ListItem(Label(f"[{len(self.mixtape_tracks)} songs] {st_name}")))
        
        mix_queue_list = self.query_one("#mix_queue_list", ListView)
        for t in formatted_tracks:
            mix_queue_list.append(ListItem(Label(t['title'])))
            
        # Clear UI list
        self.query_one("#mixtape_list", ListView).clear()
        self.mixtape_tracks.clear()
        
        self.log_msg(f"Queued Mixtape: {st_name} ({len(formatted_tracks)} tracks)")
        
        # We start the queue directly from the Mixtape tab since we have progress bars here now
        if not self.is_processing:
            self.query_one("#btn_start_queue", Button).disabled = False
            # Start queue
            self.action_start_queue()
        else:
            prog_queue = self.query_one("#prog_queue", ProgressBar)
            prog_mix_queue = self.query_one("#prog_mix_queue", ProgressBar)
            if prog_queue.total is not None:
                prog_queue.update(total=prog_queue.total + len(self.mixtape_tracks))
            if prog_mix_queue.total is not None:
                prog_mix_queue.update(total=prog_mix_queue.total + len(self.mixtape_tracks))
                
        # Clear mixtape state
        self.mixtape_tracks.clear()
        self.query_one("#mixtape_name", Input).value = ""
        self._refresh_mixtape_list()
        
        # Switch back to main tab
        self.query_one(TabbedContent).active = "tab_main"
    def action_queue_album(self) -> None:
        tree = self.query_one("#library_tree", Tree)
        
        # Collect all checked tracks grouped by album
        queued_albums = {}
        
        for artist_node in tree.root.children:
            for album_node in artist_node.children:
                album_data = album_node.data
                if not album_data:
                    continue
                    
                st_name = album_data.get("st_name")
                
                # Gather checked songs
                checked_tracks = []
                for song_node in album_node.children:
                    song_data = song_node.data
                    if song_data and song_data.get("checked"):
                        checked_tracks.append(song_data["track_data"])
                        
                        # Uncheck the song
                        song_data["checked"] = False
                        
                if checked_tracks:
                    if st_name not in queued_albums:
                        queued_albums[st_name] = []
                    queued_albums[st_name].extend(checked_tracks)
                    
                    # Uncheck the album
                    album_data["checked"] = False
                    
        if not queued_albums:
            return
            
        queue_list = self.query_one("#queue_list", ListView)
        
        total_queued_tracks = 0
        for st_name, tracks in queued_albums.items( ):
            self.album_queue.append({"st_name": st_name, "tracks": tracks})
            queue_list.append(ListItem(Label(f"[{len(tracks)} songs] {st_name}")))
            self.log_msg(f"Queued: {st_name} ({len(tracks)} tracks)")
            total_queued_tracks += len(tracks)
        
        if not self.is_processing:
            self.query_one("#btn_start_queue", Button).disabled = False
        else:
            prog_queue = self.query_one("#prog_queue", ProgressBar)
            if prog_queue.total is not None:
                prog_queue.update(total=prog_queue.total + total_queued_tracks)
        
        self._update_tree_labels()
        try:
            self.refresh_db_manager_st_list()
        except Exception:
            pass

    def action_start_queue(self) -> None:
        if not self.album_queue:
            return
            
        self.is_processing = True
        self.query_one("#btn_start_queue", Button).disabled = True
        
        self.log_msg("Starting queue processing...")
        self._process_queue_task( )
    @work(thread=True)
    def _process_queue_task(self):
        try:
            total_files_in_queue = sum(len(item["tracks"]) for item in self.album_queue)
            prog_queue = self.query_one("#prog_queue", ProgressBar)
            prog_mix_queue = self.query_one("#prog_mix_queue", ProgressBar)
            
            def init_queue_progs():
                prog_queue.update(total=total_files_in_queue, progress=0)
                prog_mix_queue.update(total=total_files_in_queue, progress=0)
                
            self.call_from_thread(init_queue_progs)

            while len(self.album_queue) > 0:
                item = self.album_queue.pop(0)
                st_name = item["st_name"]
                audio_files = item["tracks"]
                
                # remove first item from UI
                def pop_ui():
                    lv = self.query_one("#queue_list", ListView)
                    if lv.children:
                        lv.children[0].remove( )
                self.call_from_thread(pop_ui)
                
                self.call_from_thread(self.log_msg, f"Processing album: {st_name}")
                
                total_files = len(audio_files)
                prog_album = self.query_one("#prog_album", ProgressBar)
                prog_convert = self.query_one("#prog_convert", ProgressBar)
                prog_upload = self.query_one("#prog_upload", ProgressBar)
                prog_mix_track = self.query_one("#prog_mix_track", ProgressBar)
                
                def init_album_progs():
                    prog_album.update(total=total_files, progress=0)
                    prog_mix_track.update(total=total_files, progress=0)
                
                self.call_from_thread(init_album_progs)
                
                # Create ST
                st = self.stdb.add_soundtrack(st_name)
                
                for index, track_data in enumerate(audio_files):
                    fpath = track_data["path"]
                    song_name = track_data["title"]
                    filename = os.path.basename(fpath)
                    
                    self.call_from_thread(self.log_msg, f"Converting [{index+1}/{total_files}]: {song_name}...")
                    
                    # Indeterminate pulse for conversion
                    self.call_from_thread(lambda: prog_convert.update(total=None))
                    
                    fd, temp_wma = tempfile.mkstemp(suffix=".wma")
                    os.close(fd)
                    try:
                        success, result = convert_to_wma(str(fpath), temp_wma)
                        self.call_from_thread(lambda: prog_convert.update(total=100, progress=100)) # done
                        
                        if not success:
                            self.call_from_thread(self.log_msg, f"Conversion failed for {filename}: {result}")
                            continue
                            
                        time_ms = result
                        song_id = self.stdb.add_song(st.st_id, song_name, time_ms)
                        st_dir = f"{st.st_id:04x}"
                        xbox_song_id = (st.st_id << 16) | song_id
                        remote_filename = f"{xbox_song_id:08x}.wma".lower( )
                        
                        self.call_from_thread(self.log_msg, f"Uploading {remote_filename} to Xbox...")
                        
                        def prog_cb(uploaded, total):
                            self.call_from_thread(lambda: prog_upload.update(total=total, progress=uploaded))
                            
                        self.ftp.upload_wma(temp_wma, st_dir, remote_filename, progress_callback=prog_cb)
                    finally:
                        if os.path.exists(temp_wma):
                            os.unlink(temp_wma)
                            
                    def advance_album_progs():
                        prog_album.advance(1)
                        prog_mix_track.advance(1)
                        if item.get("is_mixtape"):
                            mlv = self.query_one("#mix_queue_list", ListView)
                            if mlv.children:
                                mlv.children[0].remove()
                    self.call_from_thread(advance_album_progs)
                    
                    def advance_queue_progs():
                        prog_queue.advance(1)
                        prog_mix_queue.advance(1)
                    self.call_from_thread(advance_queue_progs)
                
                self.call_from_thread(self.log_msg, f"Album {st_name} complete. Syncing ST.DB...")
                self.save_and_upload_stdb( )
                self.call_from_thread(self.refresh_st_list)
                self.call_from_thread(self._populate_library_tree)
                
            self.call_from_thread(self.log_msg, "Queue processing complete!")
            
        except Exception as e:
            self.call_from_thread(self.log_msg, f"Error processing queue: {e}")
        finally:
            self.is_processing = False
            def reenable():
                self.query_one("#btn_start_queue", Button).disabled = len(self.album_queue) == 0
                if self.selected_album:
                    self.query_one("#btn_queue", Button).disabled = False
            self.call_from_thread(reenable)


    # --- DB MANAGER LOGIC ---
    def refresh_db_manager_st_list(self) -> None:
        try:
            lv = self.query_one("#db_st_list", ListView)
            lv.clear()
            for st in self.stdb.soundtracks:
                if st.st_id not in self.db_song_order:
                    self.db_song_order[st.st_id] = list(st.songs)
                
                name = f"[{st.st_id:04x}] {st.name} ({len(st.songs)} songs)"
                if st.st_id in self.db_pending_st_deletes:
                    name = f"[red][strike]{name}[/strike][/red]"
                lv.append(ListItem(Label(name), name=str(st.st_id)))
        except Exception:
            pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "db_st_list":
            self.refresh_db_manager_song_list()
        # Handle original logic if there was any...
        
    def refresh_db_manager_song_list(self) -> None:
        try:
            st_lv = self.query_one("#db_st_list", ListView)
            song_lv = self.query_one("#db_song_list", ListView)
            song_lv.clear()
            
            if not st_lv.highlighted_child:
                return
            st_id = int(st_lv.highlighted_child.name)
            
            st = None
            for s in self.stdb.soundtracks:
                if s.st_id == st_id:
                    st = s
                    break
            if not st:
                return
                
            original_order = [song['id'] for song in st.songs]
            
            for i, song in enumerate(self.db_song_order[st_id]):
                mins = song['time'] // 60000
                secs = (song['time'] % 60000) // 1000
                name = f"{i+1}. {song['name']} ({mins}:{secs:02d})"
                
                is_deleted = (st_id, song['id']) in self.db_pending_song_deletes
                is_moved = original_order.index(song['id']) != i if song['id'] in original_order else False
                
                if is_deleted:
                    name = f"[red][strike]{name}[/strike][/red]"
                elif is_moved:
                    name = f"[yellow]{name}[/yellow]"
                    
                song_lv.append(ListItem(Label(name), name=str(song['id'])))
        except Exception:
            pass

    def action_db_st_del(self) -> None:
        st_lv = self.query_one("#db_st_list", ListView)
        if st_lv.highlighted_child:
            st_id = int(st_lv.highlighted_child.name)
            if st_id in self.db_pending_st_deletes:
                self.db_pending_st_deletes.remove(st_id)
            else:
                self.db_pending_st_deletes.add(st_id)
            self.query_one("#btn_db_sync", Button).disabled = False
            self.refresh_db_manager_st_list()
            self.refresh_db_manager_song_list()

    def action_db_song_del(self) -> None:
        st_lv = self.query_one("#db_st_list", ListView)
        song_lv = self.query_one("#db_song_list", ListView)
        if st_lv.highlighted_child and song_lv.highlighted_child:
            st_id = int(st_lv.highlighted_child.name)
            song_id = int(song_lv.highlighted_child.name)
            tup = (st_id, song_id)
            if tup in self.db_pending_song_deletes:
                self.db_pending_song_deletes.remove(tup)
            else:
                self.db_pending_song_deletes.add(tup)
            self.query_one("#btn_db_sync", Button).disabled = False
            self.refresh_db_manager_song_list()

    def action_db_song_up(self) -> None:
        st_lv = self.query_one("#db_st_list", ListView)
        song_lv = self.query_one("#db_song_list", ListView)
        if st_lv.highlighted_child and song_lv.highlighted_child:
            st_id = int(st_lv.highlighted_child.name)
            idx = song_lv.index
            if idx > 0:
                lst = self.db_song_order[st_id]
                lst[idx-1], lst[idx] = lst[idx], lst[idx-1]
                self.query_one("#btn_db_sync", Button).disabled = False
                self.refresh_db_manager_song_list()
                song_lv.index = idx - 1

    def action_db_song_down(self) -> None:
        st_lv = self.query_one("#db_st_list", ListView)
        song_lv = self.query_one("#db_song_list", ListView)
        if st_lv.highlighted_child and song_lv.highlighted_child:
            st_id = int(st_lv.highlighted_child.name)
            idx = song_lv.index
            lst = self.db_song_order[st_id]
            if idx < len(lst) - 1:
                lst[idx+1], lst[idx] = lst[idx], lst[idx+1]
                self.query_one("#btn_db_sync", Button).disabled = False
                self.refresh_db_manager_song_list()
                song_lv.index = idx + 1

    def action_db_sync(self) -> None:
        self.query_one("#btn_db_sync", Button).disabled = True
        self._db_sync_task()

    @work(thread=True)
    def _db_sync_task(self):
        try:
            self.call_from_thread(self.log_msg, "Applying DB Manager changes to Xbox...")
            
            # Deletions
            for st_id in list(self.db_pending_st_deletes):
                folder = f"{st_id:04x}"
                self.call_from_thread(self.log_msg, f"Deleting Soundtrack {folder}...")
                try:
                    self.ftp.ftp.cwd(f"{self.ftp.music_path}/{folder}")
                    files = self.ftp.ftp.nlst()
                    for f in files:
                        self.ftp.ftp.delete(f)
                    self.ftp.ftp.cwd(self.ftp.music_path)
                    folders = self.ftp.ftp.nlst()
                except Exception as e:
                    pass
                
                # Remove from local struct
                self.stdb.soundtracks = [s for s in self.stdb.soundtracks if s.st_id != st_id]
                self.db_pending_st_deletes.remove(st_id)
                if st_id in self.db_song_order:
                    del self.db_song_order[st_id]
            
            # Song deletions & reorders
            for st in self.stdb.soundtracks:
                new_songs = []
                for song in self.db_song_order[st.st_id]:
                    if (st.st_id, song['id']) in self.db_pending_song_deletes:
                        # delete file
                        wma = f"{st.st_id:04x}{(st.st_id << 16) | song['id']:08x}.wma"
                        self.call_from_thread(self.log_msg, f"Deleting track {wma}...")
                        try:
                            self.ftp.ftp.delete(f"{self.ftp.music_path}/{st.st_id:04x}/{wma}")
                        except Exception:
                            pass
                        self.db_pending_song_deletes.remove((st.st_id, song['id']))
                    else:
                        new_songs.append(song)
                st.songs = new_songs
                self.db_song_order[st.st_id] = list(new_songs)
                
            self.save_and_upload_stdb()
            self.call_from_thread(self.log_msg, "Changes synced successfully!")
            self.call_from_thread(self.refresh_st_list)
        except Exception as e:
            self.call_from_thread(self.log_msg, f"Sync error: {e}")

    # --- BACKUP OVERRIDE ---
    def action_backup(self) -> None:
        if not self.ftp:
            self.log_msg("Cannot backup: Not connected to Xbox.")
            return
            
        config = load_config()
        base_dir = os.path.expanduser(config.get("backup_dir", "~/XboxSoundtrackBackups"))
        
        name_input = self.query_one("#input_backup_name", Input).value.strip()
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bname = f"{name_input}_{timestamp}" if name_input else f"Backup_{timestamp}"
        
        backup_zip = os.path.join(base_dir, bname)
        os.makedirs(base_dir, exist_ok=True)
        
        self.log_msg(f"Starting backup to {backup_zip}.zip...")
        self.query_one("#btn_backup", Button).disabled = True
        self._backup_task(backup_zip)

    @work(thread=True)
    def _backup_task(self, backup_zip_base: str):
        try:
            import shutil, tempfile
            prog = self.query_one("#prog_backup", ProgressBar)
            self.call_from_thread(lambda: prog.update(total=None))
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # ST.DB
                self.call_from_thread(self.log_msg, "Downloading ST.DB...")
                with open(os.path.join(tmpdir, "ST.DB"), 'wb') as f:
                    self.ftp.ftp.retrbinary(f"RETR {self.ftp.music_path}/ST.DB", f.write)
                
                # Folders
                self.ftp.ftp.cwd(self.ftp.music_path)
                folders = self.ftp.ftp.nlst()
                audio_files = []
                for item in folders:
                    folder_name = os.path.basename(item)
                    if folder_name.isdigit():
                        remote_folder = f"{self.ftp.music_path}/{folder_name}"
                        local_folder = os.path.join(tmpdir, folder_name)
                        os.makedirs(local_folder, exist_ok=True)
                        try:
                            self.ftp.ftp.cwd(remote_folder)
                            files = self.ftp.ftp.nlst()
                            for f in files:
                                basename = os.path.basename(f)
                                if basename in ['.', '..']:
                                    continue
                                audio_files.append((f"{remote_folder}/{basename}", os.path.join(local_folder, basename)))
                        except Exception:
                            pass
                self.ftp.ftp.cwd(self.ftp.music_path)
                
                total_files = len(audio_files)
                if total_files > 0:
                    self.call_from_thread(lambda: prog.update(total=total_files, progress=0))
                    for i, (remote, local) in enumerate(audio_files):
                        self.call_from_thread(self.log_msg, f"Backing up [{i+1}/{total_files}]...")
                        with open(local, 'wb') as f:
                            self.ftp.ftp.retrbinary(f"RETR {remote}", f.write)
                        self.call_from_thread(lambda: prog.advance(1))
                        
                self.call_from_thread(self.log_msg, "Zipping backup...")
                shutil.make_archive(backup_zip_base, 'zip', tmpdir)
                
            self.call_from_thread(self.log_msg, f"Backup {os.path.basename(backup_zip_base)}.zip completely successfully!")
            self.call_from_thread(self.action_db_refresh_backups)
        except Exception as e:
            self.call_from_thread(self.log_msg, f"Backup failed: {e}")
        finally:
            self.call_from_thread(lambda: prog.update(total=100, progress=100))
            self.call_from_thread(lambda: setattr(self.query_one("#btn_backup", Button), 'disabled', False))

    # --- RESTORE OVERRIDE ---
    def action_db_refresh_backups(self) -> None:
        config = load_config()
        base_dir = os.path.expanduser(config.get("backup_dir", "~/XboxSoundtrackBackups"))
        if not os.path.exists(base_dir):
            return
            
        zips = [f for f in os.listdir(base_dir) if f.endswith(".zip")]
        zips.sort(reverse=True)
        
        sel = self.query_one("#select_backup", Select)
        sel.set_options([(z, z) for z in zips])

    def action_restore(self) -> None:
        if not self.ftp:
            self.log_msg("Cannot restore: Not connected to Xbox.")
            return
        sel = self.query_one("#select_backup", Select)
        if not sel.value:
            self.log_msg("Please select a backup first.")
            return
            
        config = load_config()
        base_dir = os.path.expanduser(config.get("backup_dir", "~/XboxSoundtrackBackups"))
        zip_path = os.path.join(base_dir, sel.value)
        
        def do_restore(confirm: bool):
            if confirm:
                self.log_msg(f"Restoring backup {sel.value}...")
                self.query_one("#btn_restore", Button).disabled = True
                self._restore_task(zip_path)
                
        self.push_screen(WipeConfirmScreen(), do_restore)

    @work(thread=True)
    def _restore_task(self, zip_path: str):
        try:
            import shutil, tempfile
            prog = self.query_one("#prog_restore", ProgressBar)
            self.call_from_thread(lambda: prog.update(total=None))
            
            with tempfile.TemporaryDirectory() as tmpdir:
                self.call_from_thread(self.log_msg, "Unzipping backup...")
                shutil.unpack_archive(zip_path, tmpdir, 'zip')
                
                # Wipe Xbox
                self.call_from_thread(self.log_msg, "Wiping current Xbox music...")
                self._wipe_xbox_task_sync() # need a sync wipe
                
                # Upload all
                to_upload = []
                for root, dirs, files in os.walk(tmpdir):
                    for file in files:
                        to_upload.append(os.path.join(root, file))
                        
                total = len(to_upload)
                self.call_from_thread(lambda: prog.update(total=total, progress=0))
                
                for i, local in enumerate(to_upload):
                    rel = os.path.relpath(local, tmpdir)
                    # Convert Windows backslashes to forward slashes for FTP
                    rel = rel.replace('\\', '/')
                    
                    remote = f"{self.ftp.music_path}/{rel}"
                    
                    # Ensure dir exists
                    dir_name = os.path.dirname(rel)
                    if dir_name:
                        try:
                            self.ftp.ftp.mkd(f"{self.ftp.music_path}/{dir_name}")
                        except Exception:
                            pass
                            
                    self.call_from_thread(self.log_msg, f"Restoring [{i+1}/{total}]...")
                    with open(local, 'rb') as f:
                        self.ftp.ftp.storbinary(f"STOR {remote}", f)
                    self.call_from_thread(lambda: prog.advance(1))
                    
            self.call_from_thread(self.log_msg, "Restore successful! Reconnecting...")
            self.call_from_thread(self.action_connect)
        except Exception as e:
            self.call_from_thread(self.log_msg, f"Restore failed: {e}")
        finally:
            self.call_from_thread(lambda: prog.update(total=100, progress=100))
            self.call_from_thread(lambda: setattr(self.query_one("#btn_restore", Button), 'disabled', False))

    def _wipe_xbox_task_sync(self):
        self.ftp.ftp.cwd(self.ftp.music_path)
        items = self.ftp.ftp.nlst()
        for item in items:
            if item == 'ST.DB':
                self.ftp.ftp.delete(item)
            elif '.' not in item:
                self.ftp.ftp.cwd(item)
                files = self.ftp.ftp.nlst()
                for f in files:
                    if f in ['.', '..']: continue
                    self.ftp.ftp.delete(f)
                self.ftp.ftp.cwd('..')
                self.ftp.ftp.rmd(item)


def main():
    app = XboxSoundtrackTUI( )
    app.run( )

if __name__ == "__main__":
    main( )
