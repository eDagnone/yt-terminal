import feedparser
import subprocess
import curses
import threading
from collections import namedtuple
import concurrent.futures
import yt_dlp


FRAMEBUFFER_MODE = True     # Play in Framebuffer (no X server). Requires fbdev to be installed. Overrides all other options.
FULLSCREEN = False           # Play in fullscreen mode
FORMAT = 18                  # 18 for 360p, 22 for 720p
PLAYERS = ["mplayer", "vlc", "mpv", "ffplay"]
PLAYER_INDEX = 2            # For above options.

def getStreamURL(URL):
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'verbose': False,
        'skip_download': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(URL, download=False)
        formats = info['formats']
        for format in formats:
            if(format['format_id'] == str(FORMAT)):
                return format['url'] 


def play_video(link):
    yt_dlp_str = "'" + getStreamURL(link) + "'"
    if FRAMEBUFFER_MODE:
        if PLAYER_INDEX == 0:
            command = f"mplayer -vo fbdev2 {yt_dlp_str}"
        elif PLAYER_INDEX == 1:
            command = f"vlc -I ncurses {yt_dlp_str}"
        elif PLAYER_INDEX == 2:
            command = f"mpv --vo=gpu --profile=sw-fast --framedrop=decoder --video-unscaled --vd-lavc-skipidct=bidir --vd-lavc-skiploopfilter=bidir {yt_dlp_str}"
        elif PLAYER_INDEX == 3:
            command = f"ffplay -fast -framedrop -sn -skip_loop_filter bidir -skip_idct bidir {yt_dlp_str}"
        subprocess.call(command, shell=True)
    else:
        command = f"{PLAYERS[PLAYER_INDEX]} {'-f' if FULLSCREEN else ''} {yt_dlp_str}"
        subprocess.run(command, shell=True)

Video = namedtuple('Video', ['title', 'author', 'date', 'link'])

with open("channel_ids.txt") as f:
    channel_ids = [line.strip() for line in f]

class Video:
    def __init__(self, title, author, date, link):
        self.title = title
        self.author = author
        self.date = date
        self.link = link

def gather_feed(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}&exclude=shorts"
    return feedparser.parse(url)

def parse_entry(entry):
    return Video(
        title=entry.get('title'),
        author=entry.get('author'),
        date=entry.get('published_parsed'),
        link=entry.get('link')
    )

print("Creating Threads...")
# Create a ThreadPoolExecutor with a maximum of 5 worker threads
with concurrent.futures.ThreadPoolExecutor(max_workers=len(channel_ids)) as executor:
    # Gather feeds asynchronously
    print("Pulling RSS...")
    feed_futures = [executor.submit(gather_feed, channel_id) for channel_id in channel_ids]

    videos = []
    # Process feed entries and parse them into videos
    for future in concurrent.futures.as_completed(feed_futures):
        print("Parsing...")
        feed = future.result()
        for entry in feed.entries:
            videos.append(parse_entry(entry))

print("Sorting...")
videos.sort(key=lambda entry: entry.date, reverse=True)

print("Setting up curses window...")


# Create a new curses window and pad
screen = curses.initscr()
stdscr = curses.initscr()
curses.noecho()
curses.cbreak()
stdscr.keypad(True)
max_x = curses.COLS - 1
max_y = curses.LINES - 1

pad = curses.newpad(len(videos), curses.COLS )
pad_pos = 0


# Initialize variables for scrolling
top_displayed = 0
selected = 0

# Main loop
while True:
    pad.clear()

    #Draw videos
    for i, video in enumerate(videos[top_displayed:top_displayed + max_y]):
        if i == selected:
            attr = curses.A_REVERSE
        else:
            attr = curses.A_NORMAL
        v_name = video.title
        if len(v_name) > 60:
            v_name = v_name[:60]
        ch_name = video.author
        if len(ch_name) > 16:
            ch_name = ch_name[:16]
        ch_name_formatted = f"  ({ch_name})"
        v_name_formatted = v_name.ljust(80 - len(ch_name_formatted))
        pad.addstr(i, 0, f"{v_name_formatted}{ch_name_formatted}", attr)
    pad.refresh(pad_pos, 0, 0, 0, max_y, max_x)

    # Get user input
    key = stdscr.getch()
    sel_index = top_displayed + selected
    if key == curses.KEY_UP:
        if(sel_index > 0):

            if(selected == (max_y-1)//2 and top_displayed > 0):
                top_displayed -=1   #screen scroll up
                pad_pos -=1
            else:
                selected -=1        #item scroll up

    elif key == curses.KEY_DOWN:
        if sel_index < len(videos)-1:
            if (selected == (max_y-1)//2 and top_displayed + max_y < len(videos)):
                top_displayed +=1 #screen scroll down
            else:
                selected +=1 #item scroll down
    elif key == ord('\n'):
        video = videos[top_displayed + selected]
        play_video(video.link)
        stdscr.refresh()
        stdscr.getch()
    elif key == ord('q'):
        # Quit the program
        break

# Clean up
curses.nocbreak()
stdscr.keypad(False)
curses.echo()
curses.endwin()

