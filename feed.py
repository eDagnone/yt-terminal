import feedparser
import subprocess
import curses
import threading
from collections import namedtuple
import concurrent.futures

def play_video(link):
    command = f"vlc -f $(yt-dlp -g --format 22 {link})> /dev/null 2>&1"
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
# Create a ThreadPoolExecutor with a maximum of 5 worker threads
with concurrent.futures.ThreadPoolExecutor(max_workers=len(channel_ids)) as executor:
    # Gather feeds asynchronously
    feed_futures = [executor.submit(gather_feed, channel_id) for channel_id in channel_ids]

    videos = []

    # Process feed entries and parse them into videos
    for future in concurrent.futures.as_completed(feed_futures):
        feed = future.result()
        for entry in feed.entries:
            videos.append(parse_entry(entry))

videos.sort(key=lambda entry: entry.date, reverse=True)



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
        thread = threading.Thread(target=play_video, args=(video.link,))
        thread.start()
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

