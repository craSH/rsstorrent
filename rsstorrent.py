#!/usr/bin/python
#
# Script to download .torrent files from a collection of rss feeds.
#   Copyright (C) 2009 Jamie Bennett
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#   10-03-2009 First Version jamie@linuxuk.org

# List of url feeds to be parsed. This entry is just an _example_. Please
# do not download illegal torrents or torrents that you do not have permisson
# to own.



import feedparser
import pickle
import os
import sys
import urllib2
import yaml
from datetime import datetime

items = []
feed_bad = False
current_file = " "

class rsstorrent_settings(object):
    """
    A class to hold settings which need to be passed around
    """

    feeds = []

    download_dir = ''
    timestamp = ''
    verbose = False

def read_config(settings):
    """
    Read rsstorrent config settings
    Populate settings.download_dir, settings.timestamp, settings.verbose
    """

    if not isinstance(settings, rsstorrent_settings):
        raise Exception("Improper settings object provided")

    if not os.environ.has_key('HOME'):
        raise Exception("Must have a valid home directory")

    home_dir = os.environ['HOME']
    rsstorrent_yaml = '%s/.config/rsstorrent/rsstorrent.yaml' % home_dir

    if not os.path.isfile(rsstorrent_yaml):
        print("Configuration file [%s] does not exist" % rsstorrent_yaml)
        sys.exit(1)

    try:
        f = file(rsstorrent_yaml, 'r')
        options = yaml.load(f)
    except Exception as e:
        raise Exception("Failed to load rsstorrent yaml configuration file: %s" % str(e))
    finally:
        f.close()

    try:
        settings.download_dir = options['download_dir']
        settings.timestamp = options['timestamp']
        settings.verbose = options['verbose']
        settings.feeds = options['feeds']
    except Exception as e:
        raise Exception("Failed loading configuration data from Yaml file: %s" % str(e))


    # Replace <%HOME%> with user's home dir from config if it's in any paths
    # TODO - use a real templating engine if this gets out of hand
    if settings.timestamp.find('<%HOME%>') > -1:
        settings.timestamp = settings.timestamp.replace('<%HOME%>', home_dir)

    if settings.download_dir.find('<%HOME%>') > -1:
        settings.download_dir = settings.download_dir.replace('<%HOME%>', home_dir)


def download(settings, url):
    """Copy the contents of a file from a given URL
    to a local file.
    """

    if not isinstance(settings, rsstorrent_settings):
        raise Exception("Improper settings object provided")

    try:
        remote_file = urllib2.urlopen(url)
    except urllib2.URLError as e:
        raise Exception("Unable to open URL: %s" % str(e))

    # if this isn't a torrent file (probably from mininova) add a .torrent
    # extension
    if url[-7:] != "torrent":
        url += ".torrent"

    try:
        local_file = open('%s%s' % (settings.download_dir, url.split('/')[-1]), 'w')
        local_file.write(remote_file.read())
    except urllib2.HTTPError as e:
        raise Exception("Unable to open URL: %s" % str(e))
    except Exception as e:
        raise Exception("Unable to save torrent: %s" % str(e))
    finally:
        local_file.close()
        remote_file.close()

# Build up a list of torrents to check
settings = rsstorrent_settings()
read_config(settings)
for feed_url in settings.feeds:
    feed = feedparser.parse(feed_url)

    # Valid feed ?
    if feed["bozo"] != 1:
        for item in feed["items"]:
            items.append((item["date_parsed"], item))
    else:
        if settings.verbose:
            print "bad feed: " + feed_url

        feed_bad = True

timestamp_file = " "

# Just default to now in case there is no stamp file
last_check_date = datetime.today()

# Check to read the stamp file to see when we last checked for new torrents
if os.path.isfile(settings.timestamp):
    try:
        timestamp_file = open(settings.timestamp, 'r')
    except IOError:
        if settings.verbose:
            print "Cannot open stamp file %s" % settings.timestamp

if timestamp_file != " ":
    try:
        last_check_date = pickle.load(timestamp_file)
    except EOFError:
        if settings.verbose:
            print "Stamp file %s is empty" % settings.timestamp

# Sort by date
items.sort()
new_items = []
downloaded_torrent = False

for item in items:
   # check for new items
    id = item[0]
    item_date = datetime(id[0], id[1], id[2], id[3], id[4])

    if item_date > last_check_date:
        new_items.append(item)

if len(new_items) > 0:
    download_msg = "[%s] Downloading %d torrents [" % (str(datetime.now()), len(new_items))
    # Prepare the status message
    for torrent in new_items:
        download_msg += "%s " % torrent[1]["link"]
    download_msg = download_msg[:-1] + "]"

    # Display and download the torrents
    print download_msg,
    for torrent in new_items:
        download(settings, torrent[1]["link"].encode('unicode_escape'))
        downloaded_torrent = True


if downloaded_torrent == False:
    if settings.verbose:
        print "[%s] No new torrents to download" % str(datetime.now())

if len(new_items) > 0:
    print ""

if not feed_bad and len(items) > 0:
   # stamp the timestamp file
    try:
        timestamp_file = open(settings.timestamp, 'w')
        last_item = items[len(items)-1][0]
        last_item_date = datetime(last_item[0], last_item[1], last_item[2], last_item[3], last_item[4])
        pickle.dump(last_item_date, timestamp_file)

    except IOError:
        if settings.verbose:
            print "ERROR: Cannot stamp file %s" % settings.timestamp

    finally:
        timestamp_file.close()
