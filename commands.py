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
import wikipedia as wiki
import re
import arrow
import string
import romkan
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

    def command_translate(self, event):
        '''Usage: Just use the right fucking command.'''
        self.command_tr(event)

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
                "http://e621.net/post/index.json",
                params=dict(limit="100", tags=event.params)).json()
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

    @register('nsfw', True)
    def command_randgel(self, event):
        '''Usage: ~randgel <tags> Used to search gelbooru.com for a random picture with the given tags'''
        try:
            j = requests.get(
                "https://gelbooru.com/index.php",
                params=dict(
                    page="dapi",
                    q="index",
                    json="1",
                    s="post",
                    limit="100",
                    tags=event.params)).json()
            if (len(j) > 0):
                select = random.choice(j)
                if select[u'rating'] == 's':
                    rating = 'Safe'
                elif select[u'rating'] == 'q':
                    rating = 'Questionable'
                else:
                    rating = 'Explicit'
                self.send_message(
                    event.respond,
                    u'https://gelbooru.com/index.php?page=post&s=view&id={} | Owner: {} | Rating: {} | Score: {}'.
                    format(select[u'id'], select[u'owner'], rating, select[u'score']).encode('utf-8', 'replace'))
            else:
                self.send_message(event.respond, "No Results")
        except:
            self.send_message(event.respond,
                              "An error occurred while fetching your post.")
            raise

    def command_benis(self, event):
        print(self.banned_words)
        
    @register('nsfw', True)
    def command_clop(self, event):
        '''Usage: ~clop <optional extra tags> Searches e621 for a random image with the tags rating:e and my_little_pony'''
        event.params += ' rating:e my_little_pony'
        self.command_rande621(event)

    def command_randjur(self, event):
        '''Usage: ~randjur <number> Used to post random imgur pictures, from the gallery, <number> defines the number of results with a max of 10'''
        count = 1
        if len(event.params) > 0:
            try:
                count = int(event.params)
            except:
                self.send_message(event.respond, "Could not parse parameter")
                raise
        j = requests.get(
            "https://api.imgur.com/3/gallery.json",
            headers=dict(Authorization="Client-ID " +
                         self.config['imgurKey'])).json()[u'data']
        if count > 10:
            count = 10
        images = ','.join([x[u'id'] for x in random.sample(j, count)])
        album = requests.post(
            'https://api.imgur.com/3/album/',
            headers=dict(Authorization="Client-ID " + self.config['imgurKey']),
            params=dict(ids=images)).json()[u'data'][u'id']
        self.send_message(event.respond,
                          u'http://imgur.com/a/{}'.format(album).encode(
                              'utf-8', 'replace'))

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

    def command_tr(self, event):
        '''Usage: ~translate <LanguageFrom> <LanguageTo> translates a string of text between languages. Alternate usage is ~translate list, which allows you to view currently available languages.'''
        toTrans = event.params.split()
        toTrans[0] = toTrans[0].lower()
        if toTrans[0] == 'list':
            self.send_message(event.respond, 'Here is a list of currently available languages: https://pastebin.com/j7JWk9xC')
        toTrans[1] = toTrans[1].lower()
        langs = {
            'afrikaans': 'af',
            'albanian': 'sq',
            'amharic': 'am',
            'arabic': 'ar',
            'armenian': 'hy',
            'azerbaijan': 'az',
            'bashkir': 'ba',
            'basque': 'eu',
            'belarusian': 'be',
            'bengali': 'bn',
            'bosnian': 'bs',
            'bulgarian': 'bg',
            'burmese': 'my',
            'catalan': 'ca',
            'cebuano': 'ceb',
            'chinese': 'zh',
            'croatian': 'hr',
            'czech': 'cs',
            'danish': 'da',
            'dutch': 'nl',
            'english': 'en',
            'esperanto': 'eo',
            'estonian': 'et',
            'finnish': 'fi',
            'french': 'fr',
            'galician': 'gl',
            'georgian': 'ka',
            'german': 'de',
            'greek': 'el',
            'gujarati': 'gu',
            'haitian': 'ht',
            'hebrew': 'he',
            'hill mari': 'mrj',
            'hindi': 'hi',
            'hungarian': 'hu',
            'icelandic': 'is',
            'indonesian': 'id',
            'irish': 'ga',
            'italian': 'it',
            'japanese': 'ja',
            'javanese': 'jv',
            'kannada': 'kn',
            'kazakh': 'kk',
            'khmer': 'km',
            'korean': 'ko',
            'kyrgyz': 'ky',
            'laotian': 'lo',
            'latin': 'la',
            'latvian': 'lv',
            'lithuanian': 'lt',
            'luxembourgish': 'lb',
            'macedonian': 'mk',
            'malagasy': 'mg',
            'malay': 'ms',
            'malayalam': 'ml',
            'maltese': 'mt',
            'maori': 'mi',
            'marathi': 'mr',
            'mari': 'mhr',
            'mongolian': 'mn',
            'nepali': 'ne',
            'norwegian': 'no',
            'papiamento': 'pap',
            'persian': 'fa',
            'polish': 'pl',
            'portuguese': 'pt',
            'punjabi': 'pa',
            'romanian': 'ro',
            'russian': 'ru',
            'scottish': 'gd',
            'serbian': 'sr',
            'sinhala': 'si',
            'slovakian': 'sk',
            'slovenian': 'sl',
            'spanish': 'es',
            'sundanese': 'su',
            'swahili': 'sw',
            'swedish': 'sv',
            'tagalog': 'tl',
            'tajik': 'tg',
            'tamil': 'ta',
            'tatar': 'tt',
            'telugu': 'te',
            'thai': 'th',
            'turkish': 'tr',
            'udmurt': 'udm',
            'ukrainian': 'uk',
            'urdu': 'ur',
            'uzbek': 'uz',
            'vietnamese': 'vi',
            'welsh': 'cy',
            'xhosa': 'xh',
            'yiddish': 'yi',
            'auto': ''
        }
        key = 'trnsl.1.1.20170403T165802Z.a214e2a67d20b0e6.ad95773f56547cd48cba8ecbd9dd1db0aa056c0f'

        try:
            LangFrom = langs[toTrans[0]] if toTrans[
                0] not in langs.values() else toTrans[0]
            LangTo = langs[toTrans[1]] if toTrans[
                1] not in langs.values() else toTrans[1]
        except:
            self.send_message(event.respond, 'Invalid language!')
            return
        if LangFrom!= '':
            LangFrom = LangFrom + '-'
            options = ''
        else:
            options = '&options=1'
        try:
            rep = requests.get(
                "https://translate.yandex.net/api/v1.5/tr.json/translate?key={}&text={}&lang={}{}&format=plain{}".
                format(key,
                       urllib.quote_plus(' '.join(toTrans[2:])), LangFrom,
                       LangTo,options)).json()
            text = ' '.join(rep['text'])
            if len(text) > 397:
                text = text[0:396] + '...'
            self.send_message(event.respond, text.encode('utf-8', 'replace'))
        except:
            self.send_message(
                event.respond,
                'Translation unsuccessful! Maybe the service is down?')

    def command_truerandjur(self, event):
        '''Usage: ~truerandjur <number> Used to post random imgur pictures, from randomly generated IDs, takes a little while to find images so be patient, <number> defines the number of results with a max of 10'''
        count = 1
        if len(event.params) > 0:
            try:
                count = int(event.params)
            except:
                self.send_message(event.respond, "Could not parse parameter")
                raise
        if count > 10:
            count = 10
        # this is gross, why do you let me do this python?

        def findImages(irc, count, respond, clientID):
            images = []
            while len(images) < count:
                randID = ''.join(
                    random.choice(string.ascii_letters + string.digits)
                    for x in range(0, 5))
                j = requests.get(
                    "https://api.imgur.com/3/image/" + randID,
                    headers=dict(
                        Authorization="Client-ID " + clientID)).json()
                if j[u'status'] == 200:
                    images.append(j[u'data'][u'id'])
            album = requests.post(
                'https://api.imgur.com/3/album/',
                headers=dict(Authorization="Client-ID " + clientID),
                params=dict(ids=','.join(images))).json()[u'data'][u'id']
            irc.send_message(respond,
                             u'http://imgur.com/a/{}'.format(album).encode(
                                 'utf-8', 'replace'))

        randjurThread = threading.Thread(
            target=findImages,
            kwargs=dict(
                irc=self,
                count=count,
                respond=event.respond,
                clientID=self.config['imgurKey']))
        randjurThread.start()

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
                o.text.replace('\n', '').encode('utf-8', 'replace') for o in d
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
        t = requests.get(
                    'https://www.googleapis.com/customsearch/v1',
                    params=dict(
                        q='site:imdb.com {}'.format(event.params),
                        cx=self.config['googleengine'],
                        key=self.config['googleKey'],
                        safe='off')).json()
        path = urlparse(t['items'][0]['link']).path
        movie_id = filter(bool, path.split('/'))[-1]
        headers = dict()
        headers['Content-type'] = 'application/json'
        headers['trakt-api-key'] = self.config['traktKey']
        headers['trakt-api-version'] = '2'
        try:
            resp = requests.get(
                    "https://api.trakt.tv/search/imdb/{}".format(movie_id),
                    params=dict(extended='full'),
                    headers=headers).json()[0]
            if resp.has_key('movie'):
                resp = resp['movie']
            elif resp.has_key('show'):
                resp = resp['show']
            else:
                raise ValueError()
            self.send_message(
                    event.respond,
                    u"Year: {} | Rating: {:.2f} | Runtime: {} | Plot: \x031,1{}...\x03 | http://www.imdb.com/title/{}".
                    format(resp['year'], resp['rating'],
                           resp['runtime'], resp['overview'][:199],
                           movie_id).encode('utf-8', 'replace'))
        except:
            self.send_message(event.respond,
                              "Movie not found! Try checking your spelling?")
            raise

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
                    t['items'][index]['title'], t['items'][index]['link']
            ], self.banned_words)):
                index += 1
            t = t['items'][index]
            self.send_message(event.respond, u'{}: {}'.format(
                t['title'], t['link']).encode('utf-8', 'replace'))
        except:
            self.send_message(event.respond, "No results")
            raise
    def command_weak(self, event):
        '''Usage: Check what type (or type combination) something is weak two. Prints three lines.'''
        lookup = {'normal':0,
              'fire':1,
              'water':2,
              'electric':3,
              'grass':4,
              'ice':5,
              'fighting':6,
              'poison':7,
              'ground':8,
              'flying':9,
              'psychic':10,
              'bug':11,
              'rock':12,
              'ghost':13,
              'dragon':14,
              'dark':15,
              'steel':16,
              'fairy':17,
              'none':18}
        type_list = ['Normal','Fire','Water','Electric','Grass','Ice','Fighting','Poison','Ground','Flying','Psychic','Bug','Rock','Ghost','Dragon','Dark','Steel','Fairy']
        types_input = event.params.split()
        for i in range(len(types_input)):
            types_input[i] = types_input[i].lower()

        values = []
        for item in types_input:
            if item in lookup:
                values.append(lookup[item])

        types = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.5, 0, 1, 1, 0.5, 1, 1], # Normal
    [1, 0.5, 0.5, 1, 2, 2, 1, 1, 1, 1, 1, 2, 0.5, 1, 0.5, 1, 2, 1, 1], # Fire
    [1, 2, 0.5, 1, 0.5, 1, 1, 1, 2, 1, 1, 1, 2, 1, 0.5, 1, 1, 1, 1], # Water
    [1, 1, 2, 0.5, 0.5, 1, 1, 1, 0, 2, 1, 1, 1, 1, 0.5, 1, 1, 1, 1], # Electric
    [1, 0.5, 2, 1, 0.5, 1, 1, 0.5, 2, 0.5, 1, 0.5, 2, 1, 0.5, 1, 0.5, 1, 1], # Grass
    [1, 0.5, 0.5, 1, 2, 0.5, 1, 1, 2, 2, 1, 1, 1, 1, 2, 1, 0.5, 1, 1], # Ice
    [2, 1, 1, 1, 1, 2, 1, 0.5, 1, 0.5, 0.5, 0.5, 2, 0, 1, 2, 2, 0.5, 1], # Fighting
    [1, 1, 1, 1, 2, 1, 1, 0.5, 0.5, 1, 1, 1, 0.5, 0.5, 1, 1, 0, 2, 1], # Poison
    [1, 2, 1, 2, 0.5, 1, 1, 2, 1, 0, 1, 0.5, 2, 1, 1, 1, 2, 1, 1], # Ground
    [1, 1, 1, 0.5, 2, 1, 2, 1, 1, 1, 1, 2, 0.5, 1, 1, 1, 0.5, 1, 1], # Flying
    [1, 1, 1, 1, 1, 1, 2, 2, 1, 1, 0.5, 1, 1, 1, 1, 0, 0.5, 1, 1], # Psychic
    [1, 0.5, 1, 1, 2, 1, 0.5, 0.5, 1, 0.5, 2, 1, 1, 0.5, 1, 2, 0.5, 0.5, 1], # Bug
    [1, 2, 1, 1, 1, 2, 0.5, 1, 0.5, 2, 1, 2, 1, 1, 1, 1, 0.5, 1, 1], # Rock
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 0.5, 1, 1, 1], # Ghost
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 0.5, 0, 1], # Dragon
    [1, 1, 1, 1, 1, 1, 0.5, 1, 1, 1, 2, 1, 1, 2, 1, 0.5, 1, 0.5, 1], # Dark
    [1, 0.5, 0.5, 0.5, 1, 2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 0.5, 2, 1], # Steel
    [1, 0.5, 1, 1, 1, 1, 2, 0.5, 1, 1, 1, 1, 1, 1, 2, 2, 0.5, 1, 1], # Fairy
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1] # None
    ]
        result = []
        for i in range(0,18):
            for a in range(len(values)):
                benis = functools.reduce(lambda x, y: x*y, (types[i][j] for j in values))
            result.append(benis)
        
        weak = []
        resist = []
        immune = []
        normal = []
        for i in range(0,18):
            if result[i]>=2:
                weak.append('{} ({}x)'.format(type_list[i], result[i]))
            if result[i]<1 and result[i]>0:
                resist.append('{} ({}x)'.format(type_list[i], result[i]))
            if result[i]==1:
                normal.append('{}'.format(type_list[i]))
            if result[i]==0:
                immune.append('{}'.format(type_list[i]))
        self.send_message(event.respond, 'Weak: ' + ', '.join(weak))
        self.send_message(event.respond, 'Resist: ' + ', '.join(resist))
        if immune == []:
            immune.append('None')
        self.send_message(event.respond, 'Immune: ' + ', '.join(immune))
        self.send_message(event.respond, 'Normal damage: ' + ', '.join(normal))

    def command_game(self, event):
        '''usage: too lazy to write anything here rn'''
        types = ['Normal','Fire','Fighting','Water','Flying','Grass','Poison','Electric','Ground','Psychic','Rock','Ice','Bug','Dragon','Ghost','Dark','Steel','Fairy']
        params = event.params.split()
        params[0] = int(params[0])
        to_check = []
        global to_check
        for i in range(params[0]):
            to_check.append(random.choice(types))
        event.params = ' '.join(to_check)
        self.command_weak(event)

    def command_answer(self, event):
        '''Usage: Answer the pokemon type game. Answer in the form of Type1/Type2 etc. Force display correct answer with !answer force'''
        answer = '/'.join(to_check)
        if event.params == 'force':
            self.send_message(event.respond, 'Answer is '+answer)
        elif event.params == answer:
            self.send_message(event.respond, 'Correct. Answer is '+answer)
        else:
            self.send_message(event.respond, 'Incorrect. Guess again!')
        
    def command_poke(self, event):
        '''Usage: ~poke (item/move/ability/pokemon) (name) gives a breff list of information about the input.'''
        selection = event.params.split()
        category = selection[0] 
        query = '-'.join(selection[1:])

        r = requests.get('http://pokeapi.co/api/v2/{}/{}'.format(category,query)).json()
        if category == 'item':
            try:
                result = u'{}: {}'.format(r['names'][0]['name'],r['flavor_text_entries'][1]['text']).encode('utf-8', 'replace')
                result = result.split('\n')
                result = ' '.join(result)
                self.send_message(event.respond, result)
            except:
                self.send_message(event.respond,'Unable to find item. Check your spelling?')
        elif category == 'move':
            try:
                result = u'{} | Accuracy: {} | PP: {} | Base Power: {} | Type: {} | Damage Type: {} | {}'.format(r['names'][0]['name'], r['accuracy'], r['pp'], r['power'], r['type']['name'], r['damage_class']['name'], r['effect_entries'][0]['short_effect'])
                result = result.split('\n')
                result = ' '.join(result)
                self.send_message(event.respond, result)
            except:
                self.send_message(event.respond,'Unable to find move. Check your spelling?')
        elif category == 'ability':
            try:
                result = u'{}: {}{} | https://bulbapedia.bulbagarden.net/wiki/{}_(Ability)'.format(r['names'][0]['name'],r['effect_entries'][0]['effect'][:300],'...',r['names'][0]['name']).encode('utf-8', 'replace')
                result = result.split('\n')
                result = ' '.join(result)
                self.send_message(event.respond, result)
            except:
                self.send_message(event.respond,'Unable to find ability. Check your spelling?')
        else:
            try:
                abilities = []
                types = []
                for i in range(len(r['types'])):
                    types.append(r['types'][i]['type']['name'])
                for i in range(len(r['abilities'])):
                    abilities.append(r['abilities'][i]['ability']['name'])
                result = u'Height: {}m | Weight: {}kg | Abilities: {} | Type: {}'.format(float(r['height'])/10, float(r['weight'])/10, ', '.join(abilities),
                                                                                             '/'.join(types)).encode('utf-8', 'replace')
                result = result.split('\n')
                result = ' '.join(result)
                self.send_message(event.respond, result)
            except:
                self.send_message(event.respond,'Unable to find Pokemon. Check your spelling?')
            
                
    def command_rs(self, event):
        '''Usage: ~rs <terms> Used to search for results on reddit, can narrow down to sub or user with /u/<user> or /r/<subreddit>'''
        try:
            query = event.params
            # allow searching by /r/subreddit
            srmatch = re.compile('/(r|u)/(\w+(?:\+\w+)*(?:/\S+)*)', re.I)
            srmatches = srmatch.findall(event.params)
            submatches = [s[1] for s in srmatches if s[0] == 'r']
            usermatches = [s[1] for s in srmatches if s[0] == 'u']
            terms = []
            if len(submatches) > 0:
                terms.append("subreddit:{}".format(submatches[0]))
            if len(usermatches) > 0:
                terms.append("author:{}".format(usermatches[0]))
            if len(terms) > 0:
                query = srmatch.sub("", query)
                query = query.rstrip().lstrip()
            terms.append(query)
            headers = dict()
            headers['User-Agent'] = "Berry Punch IRC Bot"
            j = requests.get(
                'https://www.reddit.com/search.json',
                params=dict(limit="1", q=' '.join(terms)),
                headers=headers).json()[u'data'][u'children']
            if len(j) > 0:
                self.send_message(event.respond,
                                  u'https://reddit.com{} - {}'.format(
                                      j[0][u'data'][u'permalink'],
                                      HTMLParser.HTMLParser().unescape(
                                          j[0][u'data'][u'title'])).encode(
                                              'utf-8', 'replace'))
            else:
                self.send_message(event.respond, 'No results.')
        except:
            self.send_message(
                event.respond,
                'Reddit probably shat itself, try again or whatever.')
            raise

    def regex_gelbooru(self, event):
        gelmatch = re.compile('https?:\/\/gelbooru\.com\/index\.php\?page=post&s=view&id=(\d{1,7})', re.I)
        res = gelmatch.findall(event.message) 
        for match in res:
            j = requests.get(
                "https://gelbooru.com/index.php",
                params=dict(
                    page="dapi",
                    q="index",
                    json="1",
                    s="post",
                    id=match)).json()
            select = random.choice(j)
            if select[u'rating'] == 's':
                rating = 'Safe'
            elif select[u'rating'] == 'q':
                rating = 'Questionable'
            else:
                rating = 'Explicit'
            self.send_message(
                    event.respond,
                    u'Owner: {} | Rating: {} | Score: {}'.
                    format(select[u'owner'], rating, select[u'score']).encode('utf-8', 'replace'))            
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
                    "https://reddit.com/r/{}".format('+'.join(subrootmatches)))
            for link in suburlmatches:
                links.append("https://reddit.com/r/{}".format(link))
            for link in usermatches:
                links.append("https://reddit.com/u/{}".format(link))
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

    def command_wimg(self, event):
        '''Usage: ~wimg <query> Searches wikipedia for the first image of a given query'''
        try:
            link = wiki.page(event.params).images[1]
            self.send_message(event.respond,
                link.encode('utf-8', 'replace'))
        except wiki.exceptions.DisambiguationError as e:
            options = u", ".join(e.options)
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
            data=dict(q=event.params)).json()['search']
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
        '''Usage: ~inflate <yearfrom> <yearto> <cost> Finds in/deflated cost of money. Only available for USD in years 1913 onwards'''
        class InflationCache(dict):
            @staticmethod
            def fetch_inflation(fromyear, toyear):
                resp = requests.get('https://data.bls.gov/cgi-bin/cpicalc.pl',
                                    params={
                                        'cost1': '1',
                                        'year1': '%s01' % fromyear,
                                        'year2': '%s01' % toyear
                                    })
                if not resp.ok:
                    raise IOError('Response from service not ok')
                html = lxml.html.fromstring(resp.text)
                val = html.xpath('//span[@id="answer"]/text()')
                if not val:
                    raise ValueError('Make sure your chosen year is in the correct range (1913-present)')
                return float(val[0][1:])

            def __missing__(self, key):
                if type(key) != tuple or len(key) != 2:
                    raise KeyError('key must be a tuple of two dates')
                fromyear, toyear = key
                self[key] = type(self).fetch_inflation(fromyear, toyear)
                return self[key]

        if not hasattr(self, 'inflation_cache'):
            self.inflation_cache = InflationCache()
        try:
            fromyear, toyear, cost = event.params.split()
            cost = float(cost)
            newcost = cost * self.inflation_cache[fromyear, toyear]
            self.send_message(
                    event.respond,
                    '${:.2f} in {} would be worth ${:.2f} in {}'.format(
                        cost, fromyear, newcost, toyear))
        except Exception as e:
            self.send_message(event.respond, "Error: {}".format(e))
            raise
    ###START Horseplay Custom Commands###

    def command_wub(self, event):
        '''Usage: ~wub Random Wubs pwny likes'''
        possibleAnswers=[
                "https://www.youtube.com/watch?v=ziFKCy1zio8",
                "https://www.youtube.com/watch?v=DYS_qFWx7-M",
                "https://www.youtube.com/watch?v=DcO6LS42BoI",
                "https://www.youtube.com/watch?v=haZbE6crALk",
                "https://www.youtube.com/watch?v=tKCfIGtvw2M",
                "https://www.youtube.com/watch?v=ga6jM4yRyHw",
                "https://www.youtube.com/watch?v=r5uAeKYy6gI",
                "https://www.youtube.com/watch?v=weQfKKcIXkA",
                "https://www.youtube.com/watch?v=KvkUY2LZ5uc",
                "https://www.youtube.com/watch?v=GXHouoD4KVM",
                "https://www.youtube.com/watch?v=PaEnaoydUUo",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://www.youtube.com/watch?v=n2ILHeP1f5Y",
                "https://www.youtube.com/watch?v=UFa-IZr9JuM",
                "https://www.youtube.com/watch?v=XxGmgmelZV0",
                "https://www.youtube.com/watch?v=8eJDTcDUQxQ",
                "https://www.youtube.com/watch?v=mDe0OBr9ehA",
                "https://www.youtube.com/watch?v=n2ILHeP1f5Y",
                "https://www.youtube.com/watch?v=3sZtd3o2kek",
                "https://www.youtube.com/watch?v=u84LSMFPgrw",
                "https://www.youtube.com/watch?v=f2NNg-k1l3U",
                "https://www.youtube.com/watch?v=gcJ0J-KdQgE",
                "https://www.youtube.com/watch?v=pMLZEZvHqeU",
                "https://www.youtube.com/watch?v=NLX_s0AcbIQ",
                "https://www.youtube.com/watch?v=_N_elu_XVeI",
                "https://www.youtube.com/watch?v=TFGtiWKy1Tk",
                "https://www.youtube.com/watch?v=lk7miDRCLec",
                "https://www.youtube.com/watch?v=_z2kc8ztlLU",
                "https://www.youtube.com/watch?v=X3lJQRjBJhU"
            ]
        self.send_message(
            event.respond,
            random.choice(possibleAnswers)
            )

    def command_kwulhu(self, event):
        possibleAnswers=[
                "Pone",
                "Pony",
                "Poner",
                "tfw not pone",
                "tfw not pony",
                "tfw not poner"
            ]
        self.send_message(
            event.respond,
            random.choice(possibleAnswers)
            )

    def command_pwny(self, event):
        possibleAnswers=[
                "Can you please ask Pwny to stop touching me?",
                "PWNY STOP BREAKING ME",
                "WHO LET PWNY HAVE ROOT ACESS?",
                "Pwny? I hate that guy",
                "Someone tell me when Pwny comes up with a good feature for me.",
                "Pwny go pls",
                "I love it when Pwny adds useless commands, like this one!",
                "Did you know that every time I say Pwny, It pings him? HEY PWNY FUCK YOU.",
                "Back in the day, I was a good IRC bot. Then Pwny attacked.",
                "Why is this even a command?",
                "Pwny is the prettiest Princess!",
                "If Pwny actually knew what he was doing, I would be a much better bot",
                "The day that Pwny is useful is the day hell freezes over",
                "PWNY SHITPOSTREADER BROKE AGAIN",
                "PWNY SHITPOSTREADER IS ACTUALLY WORKING, HOW SHOCKING",
                "Don't tell echo, but I think Pwny is my real dad",
                "On a scale of 1-Pwny, how bad are you at programing?",
                "Pwny tells me that one day I'll be a good IRC bot... One day...",
                "Heres a pwny theres a pwny and another little pwny",
                "Don't tell pwny, but I love echo more",
                "WHAT IS A PWNY BUT A MISERABLE PILE OF CODING ERRORS",
                "Someone kick the person who issued this command",
                "Psst, apparently if you type /quit you'll get an awesome prize"
            ]
        self.send_message(
            event.respond,
            random.choice(possibleAnswers)
            )

    def command_8ball(self, event):
        '''Usage: ~8ball <Query> Shakes the magic 8ball for a vague response.'''
        possibleAnswers=[
                "Fuck Yes",
                "Fuck No",
                "I have no Fucking idea",
                "I have no idea, ask Someone Else",
                "If i say yes, will you leave me alone?",
                "https://www.youtube.com/watch?v=31g0YE61PLQ",
                "Drink more and try again",
                "Yes, No and Maybe",
                "Go flip a coin or something",
                "https://www.youtube.com/watch?v=P3ALwKeSEYs",
                "After pondering your inquest most thoroughly I have come to the conclusion that one most certainly should answer positively to your question",
                "The answer to your query can be viewed by purchasing our eightball DLC! Now only $49.95! Purchase today!",
                "Do it, I FUCKING DARE YOU",
                "ERROR: PC_LOAD_LETTER",
                "ERROR: LP0_ON_FIRE",
                "oui",
                "non",
                "Yes",
                "No",
                "La La La, I CAN'T HEAR YOU!",
                "All signs point to me not giving a Shit",
                "Seek Help",
                "Jesus Christ! I hope not",
                "Ask Trips",
                "Ask Pwny",
                "Ask Esplin",
                "Ask Andy... Actually don't do that, horrible Idea.",
                "Stop touching me",
                "I love whatever that is!",
                "Thats 8/8 m8",
                "42",
                "r",
                "same",
                "Error: ID 10 T Error",
                "Ask Jeroknite",
                "In my professional opinion as a python bot, I think you should",
                "Sorry, I'm busy ignoring you",
                "You know, I think this command is biased",
                "The magic eight ball says *Go fuck yourself.*",
                "The magic eight ball says *Outlook not good*",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "Yes",
                "No",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe",
                "maybe"
            ]
        self.send_message(
            event.respond,
            random.choice(possibleAnswers)
            )

    def command_eightball(self,event):
        self.send_message(event.respond, 'use 8ball dumbass')

    def command_salt(self,event):
        self.send_message(event.respond, 'http://www.saltybet.com/ - The place where dreams go to die.')

    def command_mlas1(self,event):
        self.send_message(event.respond, 'http://www.youtube.com/watch?v=ubsz_r-pm2M')

    def command_andystrip(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=Zfp9dYktXJ0')

    def command_moe(self,event):
        self.send_message(event.respond, 'http://420.moe/')

    def command_andysong(self,event):
        self.send_message(event.respond, 'HA HA YOU KNOW WHAT SONG IT IS: http://www.youtube.com/watch?v=ubsz_r-pm2M')

    def command_horse(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=-0I-PeSXgAk')

    def command_waifu(self,event):
        self.send_message(event.respond, 'You meant Horse Wife right? http://thehorsewife.tumblr.com/')

    def command_moe(self,event):
        self.send_message(event.respond, 'http://420.moe/')

    def command_newguy(self,event):
        '''Usage: ~newguy <Nick> Link a new guy the newguy albums'''
        self.send_message(event.respond,  u'{}, please enjoy the following image albums http://imgur.com/a/9lbjH http://imgur.com/a/fyPU1'.format(event.params).encode('utf-8', 'replace'))

    def command_oldguy(self,event):
        '''Usage: ~oldguy <Nick> Link an oldfag the oldguy albums'''
        self.send_message(event.respond,  u'{}, please enjoy the following image albums http://imgur.com/a/9lbjH http://imgur.com/a/fyPU1'.format(event.params).encode('utf-8', 'replace'))

    def command_420ball(self,event):
        self.send_message(event.respond, 'xX420BlazeIt024Xx')

    def command_stats(self,event):
        '''Usage: ~stats Links the channel Statistics'''
        self.send_message(event.respond, 'Channel Statistics can be found at http://sunset.dmzirc.net/stats/')

    def command_9001(self,event):
        self.send_message(event.respond, 'ITS OVER 9000')

    def command_conky(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=e5b3mqSAqVI')

    def command_secret(self,event):
        self.send_message(event.respond, 'ITS A SECRET! https://www.youtube.com/watch?v=-3I9ThPfVqo')

    def command_0x40(self,event):
        self.send_message(event.respond, 'http://0x40hues.blogspot.com.au/')

    def command_andy(self,event):
        self.send_message(event.respond, 'MORE LIKE BIRDS AMIRITE?')

    def command_jbrony(self,event):
        self.send_message(event.respond, 'MORE LIKE J-BROWNIE AMIRITE?')

    def command_jeroknite(self,event):
        self.send_message(event.respond, 'MORE LIKE JERKINGTONITE AMIRITE?')

    def command_hitler(self,event):
        self.send_message(event.respond, 'WHY WOULD YOU EVEN THINK THAT IS A COMMAND')

    def command_esplin(self,event):
        self.send_message(event.respond, 'MORE LIKE ESPLOUT AMIRITE?')

    def command_cheesemoo(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=ONiSZbPItgo')

    def command_chat(self,event):
        self.send_message(event.respond, 'This is a Christian chat and I will not tolerate anybody here fucking swearing.')

    def command_pms(self,event):
        self.send_message(event.respond, 'FALL BACK! https://vine.co/v/Ojbg5YIwWtT')

    def command_coggler(self,event):
        self.send_message(event.respond, 'Drawfriend :3')

    def command_raribot(self,event):
        self.send_message(event.respond, 'Yes, thats me.')

    def command_friend(self,event):
        self.send_message(event.respond, 'http://i.imgur.com/SdzlIxV.jpg')

    def command_trips(self,event):
        self.send_action(event.respond, 'trips trips')

    def command_jeep(self,event):
        self.send_message(event.respond, 'BEEP BEEP IM A JEEP')

    def command_ewan(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=QK8mJJJvaes')

    def command_evan(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=QK8mJJJvaes')

    def command_scriptea(self,event):
        self.send_message(event.respond, 'SOMEONE?')

    def command_echo(self,event):
        self.send_message(event.respond, '<BAT NOISES INTENSIFY>')

    def command_clinger(self,event):
        self.send_message(event.respond, 'You could say HE IS CLINGY! HAAHAHAHAHA')

    def command_atm(self,event):
        self.send_message(event.respond, 'MORE LIKE ATTACK THE MOON AMIRITE?')

    def command_attackthemoon(self,event):
        self.send_message(event.respond, 'MORE LIKE ATM AMIRITE?')

    def command_derram(self,event):
        self.send_message(event.respond, 'SHHHHH! He-Who-Must-Not-Be-Named might hear us')

    def command_s(self,event):
        self.send_message(event.respond, 'Sweetie Bot, my sister! Oh how I love you')

    def command_sweetiebot(self,event):
        self.send_message(event.respond, 'Sweetie Bot, my sister! Oh how I love you')

    def command_cocopommel(self,event):
        self.send_message(event.respond, 'Coco Pommel is the real best pony')

    def command_evilhom3r(self,event):
        self.send_message(event.respond, 'Gay')

    def command_shitpostreader(self,event):
        self.send_message(event.respond, 'For the freshest shitposts')

    def command_risenlm(self,event):
        self.send_action(event.respond, 'sets channel papoose status on RisenLM')

    def command_minbug(self,event):
        self.send_message(event.respond, 'tfw you dont have your own chat command for your name - Minibug')

    def command_drinkiepie(self,event):
        self.send_message(event.respond, u'♫ My name is Drinkiepie ♫'.encode('utf-8', 'replace'))

    def command_books(self,event):
        self.send_action(event.respond, 'bitches angrily')

    def command_kinkinkijkin(self,event):
        self.send_message(event.respond, 'kinkinkijkin? MORE LIKE... UH... Ummmm... Shit.')

    def command_pluto(self,event):
        self.send_message(event.respond, 'Dont worry pluto, you are still a planet in my heart')

    def command_music(self,event):
        self.send_message(event.respond, 'https://www.reddit.com/r/mlas1tunes')

    def command_applejack(self,event):
        self.send_message(event.respond, 'Some ponies choose stylish injury over barbaric displays of violence.')

    def command_smooze(self,event):
        self.send_message(event.respond, 'I can see it now. When He returns, the world will be consumed by His ooze!')

    def command_twilight(self,event):
        self.send_message(event.respond, 'Im sure you and Francis will have many, many beautiful babies Twilight')

    def command_fluttershy(self,event):
        self.send_message(event.respond, 'Praise Lord Smooze, Cult Leader Fluttershy!')

    def command_spike(self,event):
        self.send_message(event.respond, 'http://gfycat.com/ZanyTallCleanerwrasse')

    def command_shipping(self,event):
        self.send_message(event.respond, 'http://gfycat.com/HairyVacantGalah')

    def command_pone(self,event):
        self.send_action(event.respond, 'turns all of chat into a pony')

    def command_othershy(self,event):
        self.send_action(event.respond, 'licks Othershy')

    def command_yiff(self,event):
        self.send_message(event.respond, 'Yiff in hell, Furfags')

    def command_repost(self,event):
        self.send_message(event.respond, 'http://i.imgur.com/UtzfmAh.gifv')

    def command_twitch(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=oWZFamqqgmA')

    def command_australia(self,event):
        self.send_message(event.respond, u'ɐqqɐƃ ǝɥʇ uᴉ noʎ ʞɔɐɯs ll,ᴉ 8ɯ ʇoʍ noʎ'.encode('utf-8', 'replace'))

    def command_commands(self,event):
        self.send_message(event.respond, 'WHY DO I HAVE SO MANY COMMANDS AND WHY ARE THEY ALL SHIT?')

    def command_ravingrbid(self,event):
        self.send_message(event.respond, 'a-wella everybodys heard about the bird bird bird bird b-birds the word')

    def command_tuckels(self,event):
        self.send_message(event.respond, 'MORE LIKE TICKLES AMIRITE?')

    def command_zooman(self,event):
        self.send_message(event.respond,  u'{} is shit'.format(event.params).encode('utf-8', 'replace'))

    def command_babs(self,event):
        self.send_message(event.respond, 'BABS SEED? MORE LIKE SWAGS WEED AMIRITE?')

    def command_chanserv(self,event):
        self.send_message(event.respond, ' MORE LIKE BANSERV AMIRITE?')

    def command_molestia(self,event):
        self.send_message(event.respond, 'All in all, that was the most touching molest-fest yet')

    def command_vidya(self,event):
        self.send_message(event.respond, 'Vidya confirmed for most casual user 2015')

    def command_mane(self,event):
        self.send_message(event.respond, 'https://www.reddit.com/r/mylittlepony/')

    def command_vidya(self,event):
        self.send_message(event.respond, 'Vidya confirmed for most casual user 2015')

    def command_horselogger(self,event):
        self.send_message(event.respond, 'Horselogger confirmed full of shit')

    def command_mtc(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=2ZNtJHX2axA')

    def command_wow(self,event):
        self.send_message(event.respond, 'w0w https://www.youtube.com/watch?v=KXebYoApByI')

    def command_name(self,event):
        self.send_message(event.respond, 'AND HIS NAME IS JOOOOHHHHNNNN CEEEEENNNNNNAAAAAAAAA')

    def command_ispwnyamod(self,event):
        self.send_message(event.respond, 'Yes unfortunately')

    def command_ket(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=l75NcBXz0fw')

    def command_lyra(self,event):
        self.send_message(event.respond, 'https://www.youtube.com/watch?v=QkYWs85k9a0')

    ###END Horseplay Custom Commands###
#test
    def regex_test(self,event):
        #substitution
        substmatch=re.compile('(?:\s|^)s/([^/]+)/([^/]+)/')
        substmatches=substmatch.findall(event.message)
        if len(substmatches) > 0:
            try:
                usernamematch = re.findall('^[a-zA-Z0-9_\-\\\[\]\{}\^`\|]+', event.message)
                if len(usernamematch) > 0 and not event.message[:2].lower() == 's/':
                    username = usernamematch[0]
                    newmessage = self.lastmessage[username].replace(substmatches[0][0], substmatches[0][1])
                    if newmessage != self.lastmessage[username]:
                        self.send_message(event.respond, '{} thinks {} meant to say: "{}"'.format(event.source, username, newmessage))
                    else:
                        self.send_message(event.respond, "Couldn't find anything to replace")
                else:
                    username = event.source
                    newmessage = self.lastmessage[username].replace(substmatches[0][0], substmatches[0][1])
                    if newmessage != self.lastmessage[username]:
                        self.send_message(event.respond, '{} meant to say: "{}"'.format(event.source, newmessage))
                    else:
                        self.send_message(event.respond, "Couldn't find anything to replace")
        
            except:
                self.send_message(event.respond, "Couldn't find anything to replace")
                raise
        
        #required for substitution
        if not hasattr(self, 'lastmessage'):
            self.lastmessage = requests.structures.CaseInsensitiveDict()
        self.lastmessage[event.source]=event.message
