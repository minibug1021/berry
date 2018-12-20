# -*- coding: utf-8 -*-
import HTMLParser
import random
import requests
import datetime
import socket
import oembed
import urllib2
import urllib
import threading
import functools
import lxml.html
import lxml.etree as etree
from lxml import html
import wikipedia as wiki
import re
import arrow
import string
import romkan
from googletrans import Translator
from urlparse import urlparse
from evaluate_function import solve_equation


def register(tag, value):
    def wrapped(fn):
        @functools.wraps(fn)
        def wrapped_f(*args, **kwargs):
            return fn(*args, **kwargs)

        setattr(wrapped_f, tag, value)
        return wrapped_f

    return wrapped


def is_str_allowed(str, bannedwords):
    for pattern in bannedwords:
        escapedv = re.escape(pattern)
        escapedv = escapedv.replace('\\*', '.*')
        matches = re.search(escapedv, str)
        if matches:
            return False
    return True


def is_all_str_allowed(strs, bannedwords):
    for str in strs:
        if not is_str_allowed(str, bannedwords):
            return False
    return True


class commands:
    def __init__(self, send_message, send_action, banned_words, config):
        self.send_message = send_message
        self.config = config
        self.send_action = send_action
        self.banned_words = banned_words

    def regex_yt(self, event):
        ytmatch = re.compile(
            "https?:\/\/(?:[0-9A-Z-]+\.)?(?:youtu\.be\/|youtube\.com\S*[^\w\-\s"
            "])([\w\-]{11})(?=[^\w\-]|$)(?![?=&+%\w]*(?:['\"][^<>]*>|<\/a>))[?="
            "&+%\w-]*",
            flags=re.I)
        matches = ytmatch.findall(event.message)
        for x in matches:
            try:
                t = requests.get(
                    'https://www.googleapis.com/youtube/v3/videos',
                    params=dict(
                        part='statistics,contentDetails,snippet',
                        fields='items/snippet/title,'
                        'items/snippet/channelTitle,'
                        'items/contentDetails/duration,'
                        'items/statistics/viewCount,'
                        'items/statistics/likeCount,'
                        'items/statistics/dislikeCount,'
                        'items/snippet/publishedAt',
                        maxResults='1',
                        key=self.config['googleKey'],
                        id=x)).json()['items'][0]

                title = t['snippet']['title']
                uploader = t['snippet']['channelTitle']
                viewcount = t['statistics']['viewCount']
                timediff = arrow.get(t['snippet']['publishedAt']).humanize()
                if 'likeCount' in t['statistics'] and 'dislikeCount' in t['statistics']:
                    likes = float(t['statistics']['likeCount'])
                    dislikes = float(t['statistics']['dislikeCount'])

                    if (dislikes > 0):
                        rating = str(int((likes /
                                          (likes + dislikes)) * 100)) + '%'
                    elif dislikes == 0 and likes == 0:
                        rating = 'unrated'
                    else:
                        rating = "100%"
                else:
                    rating = 'unrated'

                durationregex = re.compile(
                    'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', re.I)
                matches = durationregex.findall(
                    t['contentDetails']['duration'])[0]
                hours = int(matches[0]) if matches[0] != '' else 0
                minutes = int(matches[1]) if matches[1] != '' else 0
                seconds = int(matches[2]) if matches[2] != '' else 0
                duration = str(
                    datetime.timedelta(
                        hours=hours, minutes=minutes, seconds=seconds))

                viewcount = format(int(viewcount), ',')
                self.send_message(event.respond,
                                  u'{} | {} | {} | {} | {} | {}'.format(
                                      title, uploader, viewcount, timediff,
                                      rating, duration).encode(
                                          'utf-8', 'replace'))
            except:
                raise

    def command_yt(self, event):
        '''Usage: ~yt <terms> Used to search youtube with the given terms'''
        try:
            j = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params=dict(
                    part='snippet',
                    fields='items/id',
                    safeSearch='none',
                    maxResults='1',
                    key=self.config['googleKey'],
                    q=event.params)).json()
            vidid = j['items'][0]['id']['videoId']

            t = requests.get(
                'https://www.googleapis.com/youtube/v3/videos',
                params=dict(
                    part='statistics,contentDetails,snippet',
                    fields='items/snippet/title,'
                    'items/snippet/channelTitle,'
                    'items/contentDetails/duration,'
                    'items/statistics/viewCount,'
                    'items/statistics/likeCount,'
                    'items/statistics/dislikeCount,'
                    'items/snippet/publishedAt',
                    maxResults='1',
                    key=self.config['googleKey'],
                    id=vidid)).json()['items'][0]

            title = t['snippet']['title']
            uploader = t['snippet']['channelTitle']
            viewcount = t['statistics']['viewCount']
            timediff = arrow.get(t['snippet']['publishedAt']).humanize()

            if 'likeCount' in t['statistics'] and 'dislikeCount' in t['statistics']:
                likes = float(t['statistics']['likeCount'])
                dislikes = float(t['statistics']['dislikeCount'])

                if (dislikes > 0):
                    rating = str(int((likes / (likes + dislikes)) * 100)) + '%'
                else:
                    rating = "100%"
            else:
                rating = 'unrated'

            durationregex = re.compile('PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',
                                       re.I)
            matches = durationregex.findall(t['contentDetails']['duration'])[0]
            hours = int(matches[0]) if matches[0] != '' else 0
            minutes = int(matches[1]) if matches[1] != '' else 0
            seconds = int(matches[2]) if matches[2] != '' else 0
            duration = str(
                datetime.timedelta(
                    hours=hours, minutes=minutes, seconds=seconds))
            viewcount = format(int(viewcount), ',')

            self.send_message(
                event.respond,
                u'https://youtu.be/{} > {} | {} | {} | {} | {} | {}'.format(
                    vidid, title, uploader, viewcount, timediff, rating,
                    duration).encode('utf-8', 'replace'))

        except:
            self.send_message(event.respond, "No results")
            raise

    def command_g(self, event):
        '''Usage: ~g <terms> Used to search google with the given terms'''
        try:
            t = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params=dict(
                    q=event.params,
                    cx=self.config['googleengine'],
                    key=self.config['googleKey'],
                    safe='off')).json()
            index = 0
            while (len(t['items']) > index + 1 and not is_all_str_allowed([
                    t['items'][index]['title'], t['items'][index]['link']
            ], self.banned_words)):
                index += 1
            t = t['items'][index]
            self.send_message(event.respond, u'{}: {}'.format(
                t['title'], t['link']).encode('utf-8', 'replace'))
        except:
            self.send_message(event.respond, "No results")
            raise
    
    def command_tvtropes(self, event):
        '''Usage: ~tvtropes <terms> Searches TvTropes for a given trope.'''
        event.params = 'site:tvtropes.org ' + event.params
        self.command_g(event)
            
    @register('nsfw', True)
    def command_rande621(self, event):
        '''Usage: ~rande621 <tags> Used to search e621.net for a random picture with the given tags'''
        try:
            j = requests.get(
                "https://e621.net/post/index.json",
                params=dict(limit="100", tags=event.params),
                headers={'User-Agent': 'Raribot IRC Bot github.com/flare561/berry'}).json()
            if (len(j) > 0):
                try:
                    selection = random.choice(j)
                    if selection['artist'] != []:
                        artist = " & ".join(selection['artist'])
                    else:
                        artist = 'N/A'
                    if selection['rating'] == 'e':
                        rating = 'Explicit'
                    elif selection['rating'] == 's':
                        rating = 'Safe'
                    else:
                        rating = 'Questionable'
                    self.send_message(
                        event.respond,
                        u'http://e621.net/post/show/{0[id]} | Artist(s): {1} | Score: {0[score]} | Rating: {2} | Post Date: {3}'.
                        format(selection, artist, rating,
                               arrow.get(selection['created_at']['s']).format(
                                   'YYYY-MM-DD')).encode('utf-8', 'replace'))
                except:
                    self.send_message(
                        event.respond,
                        "An error occurred while fetching your post.")
            else:
                self.send_message(event.respond, "No Results")
        except:
            self.send_message(event.respond,
                              "An error occurred while fetching your post.")
            raise

    def command_randdev(self, event):
        '''Usage: ~randdev Returns a random image from Deviant Art'''
        try:
            if event.params != '':
                search_for = event.params
                source = requests.get('https://www.deviantart.com/newest/?q={}'.format(search_for)).text
            else:
                for _ in range(10):
                    search_for = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
                    source = requests.get('https://www.deviantart.com/newest/?q={}'.format(search_for)).text
                    if 'Sorry, we found no relevant results.' not in source:
                        break
            parsed = html.fromstring(source)
            results = parsed.xpath('//*[@id="page-1-results"]//*[@data-super-alt and @href]')
            final = random.choice(results)
            self.send_message(event.respond, '{} | {}'.format(final.attrib['data-super-alt'], final.attrib['href']))
        except:
            self.send_message(event.respond, 'Something is a little fucky wucky!')

    @register('nsfw', True)
    def command_randgel(self, event):
        '''Usage: ~randgel <tags> Used to search gelbooru.com for a random picture with the given tags'''
        try:
            resp = requests.get(
                "https://gelbooru.com/index.php",
                params=dict(
                    page="post",
                    s="list",
                    tags=event.params)).text
            page = html.fromstring(resp)
            links = ["https://gelbooru.com/" + x for x in 
                     page.xpath("//div[@class='thumbnail-preview']//a[@href]/@href")]
            if (len(links) > 0):
                select = random.choice(links)
                resp = requests.get(select).text
                page = html.fromstring(resp)
                rating = page.xpath("//li[starts-with(text(), 'Rating:')]/text()")[0]
                artist = " ".join(page.xpath("//li[@class='tag-type-artist']/a[2]/text()")) or "None"
                score = page.xpath("//li[starts-with(text(), 'Score:')]/span/text()")[0]
                self.send_message(
                    event.respond,
                    u'{} | Artist: {} | {} | Score: {}'.
                    format(select, artist, rating, score).encode('utf-8', 'replace'))
            else:
                self.send_message(event.respond, "No Results")
        except:
            self.send_message(event.respond,
                              "An error occurred while fetching your post.")
            raise

    @register('nsfw', True)
    def command_clop(self, event):
        '''Usage: ~clop <optional extra tags> Searches e621 for a random image with the tags rating:e and my_little_pony'''
        event.params += ' rating:e my_little_pony'
        self.command_rande621(event)

    def command_git(self, event):
            '''Usage: Links to the repository for lazy fucks. ~git <arg> will link to the line for that command, if applicable.'''
            if not event.params:
                self.send_message(event.respond, 'https://github.com/flare561/berry')
            else:
                try:
                    code = requests.get("https://raw.githubusercontent.com/flare561/berry/master/commands.py").text
                    for i, line in enumerate(code.split("\n")):
                        if "def command_{}".format(event.params) in line:
                            self.send_message(event.respond, 'https://github.com/flare561/berry/blob/master/commands.py#L{}'.format(i+1))
                            break
                    else:
                        self.send_message(event.respond, 'Command not found! Try checking your spelling?')
                except:
                    self.send_message(event.respond, 'Command not found! Maybe github is down?')

    def command_ja(self, event):
        '''Usage: ~ja <k/h/r> <arg> displays katakana/hiragana/romaji for a given argument, converting between romaji and kana'''
        try:
            dest, phrase = event.params.split(' ', 1)
            dest = dest.lower()
            if dest == 'k':
                resp = romkan.to_katakana(phrase)
            elif dest == 'h':
                resp = romkan.to_hiragana(phrase)
            elif dest == 'r':
                resp = romkan.to_roma(phrase.decode('utf-8'))
            else:
                raise
            self.send_message(event.respond, resp)
        except:
            self.send_message(event.respond, 'Invalid input, please check syntax.')
            raise

    def command_translate(self, event):
        '''Usage: Just use the right fucking command.'''
        self.command_tr(event)
            
    def command_tr(self, event):
        '''Usage: ~tr <languageTo> <phrase> The bot will auto-detect the language of the targeted text.'''
        try:
            translator = Translator()
            phrase = event.params.split() 
            translated = translator.translate(' '.join(phrase[1:]),dest= phrase[0])
            text = 'Translated from {}: {}'.format(translated.src,translated.text.encode('utf-8', 'replace'))
            if len(text) > 397:
                text = text[0:396] + '...'
            self.send_message(event.respond, text)
        except:
            self.send_message(
                event.respond,
                'Translation unsuccessful! Maybe the service is down?')
	
    def command_trs(self, event):
        '''Usage: It's like ~tr, but more specific. Use it by doing ~trs <languageFrom> <languageTo> <phrase>'''
        try:
            translator = Translator()
            phrase = event.params.split() 
            translated = translator.translate(' '.join(phrase[2:]),dest=phrase[1],src=phrase[0])
            text = 'Translated from {} to {}: {}'.format(translated.src,translated.dest,translated.text.encode('utf-8', 'replace'))
            if len(text) > 397:
                text = text[0:396] + '...'
            self.send_message(event.respond, text)
        except:
            self.send_message(
                event.respond,
                'Translation unsuccessful! Maybe the service is down?')
            raise

    def command_wolf(self, event):
        '''Usage: ~wolf <query> Searches wolfram alpha for your query'''
        try:
            s = requests.get(
                "http://api.wolframalpha.com/v2/query",
                params=dict(
                    input=event.params, appid=self.config['wolframKey'])).text

            x = etree.fromstring(s.encode('UTF-8', 'replace'))
            d = x.xpath('//pod[@primary="true"]/subpod/plaintext')

            results = [
                o.text.replace('\n', ' ').encode('utf-8', 'replace') for o in d
            ]

            search_url = "http://www.wolframalpha.com/input/?i={}".format(
                urllib.quote(event.params, ''))

            if len(results) < 1:
                responseStr = "No results available, try the query page:"
            else:
                responseStr = '; '.join(results)

            if (len(responseStr) + len(search_url)) > 390:
                responseStr = responseStr[:(390 - len(search_url))] + "..."

            responseStr += " " + search_url

            self.send_message(event.respond, responseStr)
        except:
            self.send_message(event.respond, "Error with the service")
            raise

    def command_weather(self, event):
        '''Usage: ~weather <location> Gets the weather for a location from wolfram alpha'''
        event.params = 'weather ' + event.params
        self.command_wolf(event)

    def command_define(self, event):
        '''Usage: ~define <word> Gets the definition of a word from wolfram alpha'''
        event.params = 'define ' + event.params
        self.command_wolf(event)

    def command_imdb(self, event):
        '''Usage: ~imdb <movie title> Provides basic information of a given movie, if applicable.'''
	try:
		t = requests.get(
						'https://www.googleapis.com/customsearch/v1',
						params=dict(
							q='site:imdb.com {}'.format(event.params),
							cx=self.config['googleengine'],
							key=self.config['googleKey'],
							safe='off')).json()
		link = requests.get(t['items'][0]['link']).text
		
		parsed = html.fromstring(link)
		
		def xpath(page, expr, process=lambda x: x.text, index=0):
			try:
				return process(page.xpath(expr)[index])
			except IndexError:
				return None
			
		
		year = xpath(parsed, '//*[@id="titleYear"]/a') or \
			xpath(parsed, '//span[@class="parentDate"]', lambda x: x.text[1:-1]) or \
			xpath(parsed, '//a[@title="See more release dates"]', lambda x: x.text[11:-2])
		
		rating = xpath(parsed, '//meta[@itemprop="contentRating"]/@content', lambda x: x) or \
				'Not Rated'
		
		length = xpath(parsed, '//time[@itemprop="duration"]', index=1) or \
				'None'
		
		score = xpath(parsed, '//span[@itemprop="ratingValue"]') or \
				'Needs 5 ratings'
		
		movie_summary = parsed.xpath('//div[@class="summary_text"]')[0].text.strip()
		if not movie_summary:
			movie_summary = 'No summary available'
		self.send_message(event.respond, u"Year: {} | Rating: {} | Length: {} | Score: {} | Summary: {} | {}"
		.format(year,rating,length,score,movie_summary,t['items'][0]['link']).encode('utf-8', 'replace'))
	except:
		self.send_message(event.respond, 'No results! Check your spelling?')
		
    def command_test(self, event):
        '''Usage: ~test Used to verify the bot is responding to messages'''
        possibleAnswers = [
            "Cake, and grief counseling, will be available at the conclusion of the test.",
            "Remember, the Aperture Science Bring Your Daughter to Work Day is the perfect time to have her tested.",
            "As part of an optional test protocol, we are pleased to present an amusing fact: The device is now more valuable than the organs and combined incomes of everyone in *subject hometown here.*",
            "The Enrichment Center promises to always provide a safe testing environment. In dangerous testing environments, the Enrichment Center promises to always provide useful advice. For instance: the floor here will kill you. Try to avoid it.",
            "Due to mandatory scheduled maintenance, the next test is currently unavailable. It has been replaced with a live-fire course designed for military androids. The Enrichment Center apologizes and wishes you the best of luck. ",
            "Well done. Here are the test results: You are a horrible person. I'm serious, that's what it says: \"A horrible person.\" We weren't even testing for that."
        ]
        self.send_message(event.respond, random.choice(possibleAnswers))

    def command_select(self, event):
        '''Usage: ~select <args> Used to select a random word from a given list'''
        if len(event.params) > 0:
            selection = [x for x in event.params.split(' ') if x != '']
            self.send_message(
                event.respond,
                'Select: {}'.format(random.choice(selection)))
        else:
            self.send_message(event.respond, "Invalid parameters. Please include arguements.")

    def command_flip(self, event):
        '''Usage: ~flip Used to flip a coin, responds with heads or tails'''
        self.send_message(event.respond,
                          'Flip: {}'.format(random.choice(['Heads', 'Tails'])))

    def command_gr(self, event):
        '''Usage: ~gr <query> links to the google results for a given query'''
        self.send_message(
            event.respond,
            "http://google.com/#q={}".format(urllib.quote(event.params, '')))

    def command_roll(self, event):
        '''Usage: ~roll <x>d<n> rolls a number, x, of n sided dice, example: ~roll 3d20'''
        strippedparams = ''.join(event.params.split())
        args = strippedparams.split('d')
        try:
            numDice = int(args[0])
        except:
            self.send_message(
                event.respond,
                "Invalid parameters, expected format is <int>d<int> Example: 1d6"
            )
            raise
        try:
            dieSize = int(args[1])
        except:
            self.send_message(
                event.respond,
                "Invalid parameters, expected format is <int>d<int> Example: 1d6"
            )
            raise
        if numDice > 10 or dieSize > 100:
            self.send_message(
                event.respond,
                "The Maximum number of dice is 10, and the maximum number of sides is 100"
            )
        else:
            self.send_message(
                event.respond, "Results: {}".format(', '.join([
                    str(random.randint(1, dieSize)) for x in range(numDice)
                ])))

    def ud(self, event, sort=None):
        try:
            rank = max(1, int(event.params.split('  ')[-1]))
        except ValueError:
            rank = 1

        index = rank - 1

        def calc_score(json):
            total = json.get('thumbs_up', 0) + json.get('thumbs_down', 0)
            return ((json.get('thumbs_up', 0) * 100) // total) if total > 0 else 0

        if sort is None:
            sort = calc_score

        try:
            word = event.params.split('  ')[0]
            k = requests.get("http://api.urbandictionary.com/v0/define",
                             params=dict(term=word)
                             ).json()[u'list']
            k.sort(key=sort, reverse=True)
            k = k[index]
            definition = re.sub(r'[\r\n]', ' ', k['definition'].encode('UTF-8', 'replace'))
            if (len(definition) > 380):
                definition = "{}...".format(definition[:380])
            response = "#{}: {} | Score: {}/{} {}% | {}".format(
                rank,
                definition,
                k['thumbs_up'],
                k['thumbs_down'],
                str(calc_score(k)),
                k['permalink']
            )
            self.send_message(event.respond, response)
        except:
            self.send_message(event.respond, "An error occurred while fetching your post, or there are no results.")
            raise

    def command_ud(self, event):
        '''Usage: ~ud <query>\s\s<int n> Used to search Urban Dictionary for the first (or nth) definition of a word, using flat upvote rank style. Note: a double space is required between parameters'''
        self.ud(event, sort=lambda x: x.get('thumbs_up', 0))

    def command_udr(self, event):
        '''Usage: ~udr <query>\s\s<int n> Used to search Urban Dictionary for the first (or nth) definition of a word, using ratio (upvotes/downvotes) rank style. Note: a double space is required between parameters'''
        self.ud(event)

    def command_isup(self, event):
        '''Usage: ~isup <site> used to check if a given website is up using isup.me'''
        try:
            s = requests.get("http://isup.me/{}".format(event.params)).text
            if "It's just you." in s:
                response = "It's just you! {} is up!".format(event.params)
            else:
                response = "It's not just you! {} looks down from here!".format(
                    event.params)
            self.send_message(event.respond, response)
        except:
            self.send_message(event.respond, "Error with the service")
            raise

    def command_gimg(self, event):
        '''Usage: ~gimg <terms> Used to search google images with the given terms'''
        try:
            t = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params=dict(
                    q=event.params,
                    cx=self.config['googleengine'],
                    key=self.config['googleKey'],
                    safe='off',
                    searchType='image')).json()
            index = 0
            while (len(t['items']) > index + 1 and not is_all_str_allowed([
                    t['items'][index]['link']
            ], self.banned_words)):
                index += 1
            t = t['items'][index]
            self.send_message(event.respond, u'{}'.format(
                t['link']).encode('utf-8', 'replace'))
        except:
            self.send_message(event.respond, "No results")
            raise

    def command_rs(self, event):
        '''Usage: ~rsearch <submission/comment> <subreddit> <author> <query> Subreddit and Author are optional, replace with 'any' if not needed.'''
        init = event.params.split()
        print(init)
        search_type, query, subreddit, author = init[0],' '.join(init[3:]),init[1],init[2]
        subreddit = '' if subreddit == 'any' else subreddit
        author = '' if author == 'any' else author
        try:
            a = requests.get('https://api.pushshift.io/reddit/search/{}/?q={}&subreddit={}&author={}&size=50'.format(search_type,query,subreddit,author).strip('')).json()
        except:
            self.send_message(event.respond, 'you broke something try again')
        if len(a['data']) == 0:
            self.send_message(event.respond, 'There were no results for your search')
            raise
        selection = random.choice(a['data'])
        if search_type == 'submission':
            permalink = 'https://old.reddit.com/{}'.format(selection["id"])
            self.send_message(event.respond, '{}: {} | {}'.format(selection['author'], selection['title'].encode('utf-8', 'replace')[:500-len(selection['title'])],permalink))
        else:
            selection['link_id'] = selection['link_id'][3:]
            permalink = 'https://old.reddit.com/r/{subreddit}/comments/{link_id}//{id}'.format(**selection)
            self.send_message(event.respond, '{}: {} | {}'.format(selection['author'], selection['body'].encode('utf-8', 'replace')[:500-len(selection['body'])],permalink))

    def regex_gelbooru(self, event):
        gelmatch = re.compile('https?:\/\/gelbooru\.com\/index\.php\?page=post&s=view&id=(\d{1,7})', re.I)
        res = gelmatch.findall(event.message) 
        for match in res:
            resp = requests.get(
                "https://gelbooru.com/index.php",
                params=dict(
                    page="post",
                    s="view",
                    id=match)).text
            page = html.fromstring(resp)
            rating = page.xpath("//li[starts-with(text(), 'Rating:')]/text()")[0]
            artist = " ".join(page.xpath("//li[@class='tag-type-artist']/a[2]/text()")) or "None"
            score = page.xpath("//li[starts-with(text(), 'Score:')]/span/text()")[0]
            self.send_message(
                event.respond,
                u'Artist: {} | {} | Score: {}'.
                format(artist, rating, score).encode('utf-8', 'replace'))
            
            
    def regex_e621(self, event):
        e621match = re.compile('https?:\/\/e621\.net\/post\/show\/\d{2,7}',
                               re.I)
        res = e621match.findall(event.message)
        for link in res:
            select = link + '.json'
            selection = requests.get(select).json()
            if selection['artist'] != []:
                artist = " & ".join(selection['artist'])
            else:
                artist = 'N/A'
            if selection['rating'] == 'e':
                rating = 'Explicit'
            elif selection['rating'] == 's':
                rating = 'Safe'
            else:
                rating = 'Questionable'
            self.send_message(
                event.respond,
                u'Artist(s): {1} | Score: {0[score]} | Rating: {2} | Post Date: {3}'.
                format(selection, artist, rating,
                       arrow.get(selection['created_at']['s']).format(
                           'YYYY-MM-DD')).encode('utf-8', 'replace'))

    def regex_reddit(self, event):
        if not event.command.lower()[1:] == 'rs':
            srmatch = re.compile('(?<!\S)/(r|u)/(\w+(?:\+\w+)*(?:/\S+)*)',
                                 re.I)
            srmatches = srmatch.findall(event.message)
            subrootmatches = [
                s[1] for s in srmatches if s[0] == 'r' and '/' not in s[1]
            ]
            suburlmatches = [
                s[1] for s in srmatches if s[0] == 'r' and '/' in s[1]
            ]
            usermatches = [s[1] for s in srmatches if s[0] == 'u']
            links = []
            if len(subrootmatches) > 0:
                links.append(
                    "https://old.reddit.com/r/{}".format('+'.join(subrootmatches)))
            for link in suburlmatches:
                links.append("https://old.reddit.com/r/{}".format(link))
            for link in usermatches:
                links.append("https://old.reddit.com/u/{}".format(link))
            if len(links) > 0:
                self.send_message(event.respond, ' '.join(links))

    def command_dns(self, event):
        '''Usage: ~dns <domain> Used to check which IPs are associated with a DNS listing'''
        try:
            records = socket.getaddrinfo(event.params.split(' ')[0], 80)
            addresses = set([x[4][0] for x in records])
            self.send_message(event.respond, " ".join(addresses))
        except:
            self.send_message(event.respond,
                              "You must give a valid host name to look up")

    def command_mal(self, event):
        '''Usage: ~mal <query> Searches My Anime List for a given anime using a custom google search'''
        try:
            t = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params=dict(
                    q=event.params,
                    cx=self.config['googleengine'],
                    key=self.config['googleKey'],
                    safe='off',
                    siteSearch='myanimelist.net')).json()['items'][0]
            self.send_message(event.respond, u'{}: {}'.format(
                t['title'], t['link']).encode('utf-8', 'replace'))
        except:
            self.send_message(event.respond, "No results")
            raise

    def regex_deviantart(self, event):
        damatch = re.compile(
            '((?:(?:https?|ftp|file)://|www\.|ftp\.)(?:\([-A-Z0-9+&@#/%=~_|$?!:,.]*\)|[-A-Z0-9+&@#/%=~_|$?!:,.])*(?:\([-A-Z0-9+&@#/%=~_|$?!:,.]*\)|[A-Z0-9+&@#/%=~_|$]))',
            re.I)
        damatches = damatch.findall(event.message)
        for x in damatches:
            try:
                consumer = oembed.OEmbedConsumer()
                endpoint = oembed.OEmbedEndpoint(
                    'http://backend.deviantart.com/oembed', [
                        'http://*.deviantart.com/art/*', 'http://fav.me/*',
                        'http://sta.sh/*', 'http://*.deviantart.com/*#/d*'
                    ])
                consumer.addEndpoint(endpoint)
                response = consumer.embed(x).getData()
                out = []
                if 'title' in response:
                    out.append("Title: {}".format(response[u'title']))
                if 'author_name' in response:
                    out.append("Artist: {}".format(response[u'author_name']))
                if 'rating' in response:
                    out.append("Rating: {}".format(response[u'rating']))
                if 'url' in response:
                    out.append("Direct Url: {}".format(response[u'url']))
                self.send_message(event.respond, " | ".join(out).encode(
                    'utf-8', 'replace'))
            except oembed.OEmbedNoEndpoint:
                pass
            except urllib2.HTTPError:
                pass

    def command_wiki(self, event):
        '''Usage: ~wiki <query> Searches wikipedia for a given query'''
        try:
            page = wiki.page(event.params)
            summary = page.summary.replace('\n', ' ')
            url = page.url
            maxlen = 381 - len(url)
            resp = u"{}... | {}".format(summary[:maxlen], url)
            self.send_message(event.respond, resp)
        except wiki.exceptions.DisambiguationError as e:
            url = "https://en.wikipedia.org/wiki/%s" % urllib.quote_plus("_".join(event.params.split()))
            maxlen = 381 - len(url)
            options = u", ".join(e.options)
            options = u"{}... | {}".format(options[:maxlen], url)
            self.send_message(event.respond, options)
        except:
            self.send_message(event.respond, "No results")
            raise

    def command_feels(self, event):
        self.send_message(event.respond,
                          'http://imgur.com/a/PJIsu/layout/blog')

    def command_lenny(self, event):
        self.send_message(event.respond, u'( ͡° ͜ʖ ͡°)'.encode(
            'utf-8', 'replace'))

    def command_derpi(self, event):
        '''Usage: ~derpi <query> Searches derpibooru for a query, tags are comma separated.'''
        sess = requests.Session()
        page = lxml.html.fromstring(
            sess.get('https://derpibooru.org/filters').text)
        authenticitytoken = page.xpath('//meta[@name="csrf-token"]')[0].attrib[
            'content']
        body = dict()
        body['authenticity_token'] = authenticitytoken
        body['_method'] = 'patch'
        sess.post(
            'https://derpibooru.org/filters/select?id=56027',
            data=body,
            headers=dict(Referer='https://derpiboo.ru/filters'))
        if event.params == "":
            event.params = "*"
        results = sess.get(
            'https://derpibooru.org/search.json',
            data=dict(q=event.params, filter_id='56027')).json()['search']
        if len(results) > 0:
            choice = random.choice(results)
            idNum = choice['id']
            self.send_message(event.respond,
                              ('https://derpibooru.org/%s' % idNum).encode(
                                  "utf-8", "replace"))
        else:
            self.send_message(event.respond, 'No results'.encode(
                "utf-8", "replace"))

    def command_sderpi(self, event):
        '''Usage: ~sderpi <query> Searches derpibooru for a query, sorted by score, tags are comma separated.'''
        sess = requests.Session()
        page = lxml.html.fromstring(
            sess.get('https://derpibooru.org/filters').text)
        authenticitytoken = page.xpath('//meta[@name="csrf-token"]')[0].attrib[
            'content']
        body = dict()
        body['authenticity_token'] = authenticitytoken
        body['_method'] = 'patch'
        sess.post(
            'https://derpibooru.org/filters/select?id=56027',
            data=body,
            headers=dict(Referer='https://derpiboo.ru/filters'))
        if event.params == "":
            event.params = "*"
        results = sess.get(
            'https://derpibooru.org/search.json',
            data=dict(q=event.params, filter_id='56027', sf='score', sd='desc')).json()['search']
        if len(results) > 0:
            choice = random.choice(results)
            idNum = choice['id']
            self.send_message(event.respond,
                              ('https://derpibooru.org/%s' % idNum).encode(
                                  "utf-8", "replace"))
        else:
            self.send_message(event.respond, 'No results'.encode(
                "utf-8", "replace"))

    def command_pony(self, event):
        '''Usage: ~pony Gives time until next episode of mlp'''
        now = datetime.datetime.utcnow()
        if True:  # now < datetime.datetime(2015,7,11,15,30):
            days_ahead = 5 - now.weekday()
            if days_ahead < 0 or (days_ahead == 0 and
                                  now.time() > datetime.time(15, 30)):
                days_ahead += 7
            next_episode = datetime.datetime.combine(
                now.date() + datetime.timedelta(days_ahead),
                datetime.time(15, 30))
            time_remaining = (next_episode - now).seconds
            hours, remainder = divmod(time_remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.send_message(
                event.respond,
                "Time until next episode: {} days {} hours {} minutes {} seconds".
                format((next_episode - now).days, hours, minutes, seconds))
        else:
            self.send_message(event.respond,
                              "The show is on hiatus until later this year.")

    def regex_fwt(self, event):
        fwtre = re.findall(r'`(.*?)`', event.message)
        if fwtre:
            event.params = ''.join(fwtre)
            self.command_fwt(event)

    def command_fwt(self, event):
        '''Usage: ~fwt <text> repeats text in full width and adds spaces for A E S T H E T I C S'''
        self.send_action(event.respond, (u" ".join([
            unichr(ord(x) + 65248) if 32 < ord(x) < 127 else x
            for x in event.params
        ])).encode('utf-8', 'replace'))

    @register('nsfw', True)
    def command_furry(self, event):
        '''Usage: ~furry <nick> yiffs them'''
        yiff = random.choice(self.config['yiffs'])
        self.send_action(event.respond, (
            yiff.replace('$target', event.params.strip()).replace(
                '$user', 'pwny').replace('$nick', self.config['nick']).replace(
                    '$channel', event.respond)).encode('utf-8', 'replace'))

    def command_math(self, event):
        '''Usage: ~math <equation> solves a math equation with support for basic functions'''
        try:
            result = solve_equation(event.params)
            self.send_message(event.respond, str(result))
        except Exception:
            self.command_wolf(event)

    def command_inflate(self, event):
        '''Usage: ~inflate <yearfrom> <yearto> <cost> Finds in/deflated cost of money. Only available for USD in years 1665 to 2018.'''
        try:
            start,end,amount = event.params.split()
            amount = float(amount)
            r = requests.get('http://www.in2013dollars.com/{}-dollars-in-{}?amount={}'.format(start,end,amount)).text
            parsed = html.fromstring(r)
            adjusted = parsed.xpath('//*[@class="highlighted-amount"]')[1].text
            self.send_message(event.respond, '${} in {} would be worth {} in {}'.format(amount,start,adjusted,end))
        except:
            self.send_message(event.respond, 'An error has occured, please double-check your input')
