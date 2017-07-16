# -*- coding: utf-8 -*-
# ---------------
# VK Page Manager - script for automatic parsing news sites and rss. parsed news uploading
# into vkontakte public page using api in vk library 
# Using kivy and kivymd for GUI like material design(android)
# NOTE for each site  individual block of code(parsing unique html pattern)

# Bohdan Sapovsky COPYRIGHT 2016
# --------------


import csv
import sys
import logging
import copy
import time
import random
import threading

import requests
from bs4 import BeautifulSoup as Bs
import vk
import feedparser

import kivy

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock, mainthread
from kivymd.theming import ThemeManager
from kivymd.list import IRightBodyTouch, ThreeLineAvatarIconListItem
from kivymd.selectioncontrols import MDCheckbox

kivy.require('1.9.1')

VK_LOGIN = 'YOUR LOGIN'
VK_PASSWORD = 'YOUR PASSWORD'
VERSION = '1.1.7'


###################################################
# Checkbox windget in posts window
class PostButt(IRightBodyTouch, MDCheckbox):
    def on_state(self, *args):
        super().on_state(*args)
        return App.get_running_app().root.on_post_button_release(self)


################################################
# Mainwindow(Root) widget
class VpmRoot(BoxLayout):
    global VERSION

    def __init__(self, **kwargs):
        super(VpmRoot, self).__init__(**kwargs)
        self.ids.loglabel.text = '  Initialization... %s' % VERSION
        self.ids.sendButton.disabled = True
        self.posts = []
        self.send_posts = []
        self.reload_timer = False
        self.COUNTER = 60  # Counter for relauch parsing
        self.reload_counter = self.COUNTER
        self.auto_pilot = False

    # Updating text in log window
    @mainthread
    def update_text(self, text):
        self.ids.loglabel.text += text

    # Change text in reload text window. If counter == 0 - run parser
    def reload_text(self, dt):
        if self.reload_counter == 0:
            Clock.unschedule(self.reload_timer)
            self.runt()
        else:
            self.reload_counter -= 1
            self.ids.rLabel.text = 'Reload in %s m' % self.reload_counter

    # Create and run parser to crawl news in new thread
    def runt(self, **kwargs):
        try:
            App.get_running_app().change_theme()
            if self.reload_timer:
                Clock.unschedule(self.reload_timer)
                self.ids.rLabel.text = ' '
            self.ids.pLayout.disabled = False
            self.ids.startButton.disabled = True
            self.ids.pLayout.clear_widgets() if self.posts else None
            self.ids.spinner.active = True
            self.update_text('\n Starting parser...' + time.strftime('[%c]', time.localtime()))
            parser = PostParser(self.update_text, self.ready)
            thread = threading.Thread(target=parser.load_posts)
            thread.start()
        except RuntimeError:
            logging.error('\n Error: [{}] : [{}]'.format(sys.exc_info()[0], sys.exc_info()[1]))
            self.update_text('\n Error: [{}] : [{}]'.format(sys.exc_info()[0], sys.exc_info()[1]))

    # Called when parser have done it's work. Also manage result of
    # parsing which hold in future variable
    def ready(self, future=None):
        self.ids.startButton.disabled = False
        self.ids.spinner.active = False
        self.reload_counter = self.COUNTER
        if future:
            self.posts = copy.deepcopy(future)
            self.show_posts()
        else:
            self.ids.pLayout.clear_widgets()
            self.reload_timer = Clock.schedule_interval(self.reload_text, 60)
            self.ids.rLabel.text = 'Reload in 60m'

    # Add posts to widget with checkbox to main window
    def show_posts(self):
        for post in self.posts:
            title = post.get_post().split('.')
            item = ThreeLineAvatarIconListItem(text=post.get_hashtag(), secondary_text=title[0])
            self.ids.pLayout.add_widget(item)
            item.add_widget(PostButt(id=str(self.posts.index(post))))
        if self.auto_pilot:
            self.send_posts = copy.deepcopy(self.posts)
            self.on_send(self)

    # This for count which posts should be uploaded
    def on_post_button_release(self, widget):
        if widget.state == 'down':
            self.send_posts.append(self.posts[int(widget.id)])
        elif widget.state == 'normal':
            try:
                self.send_posts.remove(self.posts[int(widget.id)])
            except ValueError:
                self.update_text('\n Error! Trying to delete element for post doesn\'t exist!')
        if self.send_posts:
            self.ids.sendButton.disabled = False
        else:
            self.ids.sendButton.disabled = True

    # Creating new thread for upload news
    def on_send(self, widget):
        self.ids.startButton.disabled = True
        self.ids.sendButton.disabled = True
        self.ids.pLayout.disabled = True
        try:
            self.ids.spinner.active = True
            self.update_text('\n Preparing uploading posts...')
            uploader = PostUploader(self.update_text, self.send_posts, self.ready)
            thread = threading.Thread(target=uploader.send_posts)
            thread.start()
        except RuntimeError:
            logging.info('\n Error: [{}] : [{}]'.format(sys.exc_info()[0], sys.exc_info()[1]))
            self.ids.loglabel.text += '\n Error: [{}] : [{}]'.format(sys.exc_info()[0], sys.exc_info()[1])

    # Simple function for autopilot switcher
    def auto_pilot_switcher(self, widget):
        self.auto_pilot = widget.active
        self.update_text('\n [Autopilot activated]') if widget.active else self.update_text(
            '\n [Autopilot deactivated]')


###############################################
class VpmApp(App):
    theme_cls = ThemeManager()
    icon = 'icon.ico'
    title = 'Vk Page Manager'
    thems_palette = ('Pink', 'Blue', 'Indigo', 'BlueGrey', 'Brown',
                     'LightBlue',
                     'Purple', 'Grey', 'Yellow', 'LightGreen', 'DeepOrange',
                     'Green', 'Red', 'Teal', 'Orange', 'Cyan', 'Amber',
                     'DeepPurple', 'Lime')

    def change_theme(self):
        self.theme_cls.primary_palette = random.choice(self.thems_palette)

    def build(self):
        return VpmRoot()


################################################
# Model for posts
class PostModel:
    __slots__ = ('__post', '__hashtag', '__link', '__img')

    def __init__(self, p=None, h=None, l=None, i=None, **kwargs):
        self.__post = p
        self.__hashtag = h
        self.__link = l
        self.__img = i

    def set_img(self, i):
        self.__img = i

    def set_link(self, l):
        self.__link = l

    def set_post(self, p):
        self.__post = p

    def set_hashtag(self, h):
        self.__hashtag = h

    def get_post(self):
        return self.__post

    def get_hashtag(self):
        return self.__hashtag

    def get_link(self):
        return self.__link

    def get_img(self):
        return self.__img


################################################
# Scrapp news from web sites
class PostParser:
    def __init__(self, conn=None, cond=None, **kwargs):
        self.conn = conn  # This handle update_text function
        self.cond = cond  # This handle ready function from VpmRoot

    # Sending log text via update_text func in VpmRoot
    def send(self, message):
        self.conn(message[1])

    # Get last posts link in memory.csv
    def get_last_post(self, *args, **kwargs):
        lp = []
        self.send(['log', '\n Loading last posts list...'])
        with open('memory.csv', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                lp.append(row)
        self.send(['log', '\n Finished!...'])
        return lp

    # Writing new last posts link to memory.csv
    def write(self, posts, **kwargs):
        self.send(['log', '\n Writing new last posts...'])
        with open('memory.csv', 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for post in posts:
                writer.writerow(post)
        self.send(['log', '\n Writing finished!...'])

    # Actually parsing procces
    def load_posts(self):
        ukurier_login = 'agentx'
        ukurier_password = 'agentx'
        t0 = time.time()
        self.send(['log', '\n Starting parsing sites...'])
        LAST_POST = self.get_last_post()  # It should mark as static for while
        new_post = ''
        posts = []
        imgs = {'news': 'photo-94269795_427353655', 'acts': 'photo-94269795_427351011',
                'expert': 'photo-94269795_430949899'}
        hashtags = {'acts': '#Нормативні_акти_міністерств_і_відомств#Корисні_документи#Урядовий_кур\'єр',
                    'laws': '#Законодавство#Нові_папірці', 'news':
                        '#Новини#Корисна_інформація#Юридична_Газета', 'expert': '#Думка_експерта#Юридична_газета',
                    'expert_protokol': '#Думка_експерта#Протокол'}
        self.send(['log', '\n List of last posts loaded!...'])
        s = requests.Session()
        try:
            req = s.get('http://ukurier.gov.ua/uk/archive/documents/')
            soup = Bs(req.text, 'html.parser')
            secret = soup.find('input', attrs={'name': 'csrfmiddlewaretoken'})
            req = s.post('http://ukurier.gov.ua/uk/accounts/login/',
                         data={'csrfmiddlewaretoken': secret['value'], 'id_username': 'stPhoenix',
                               'username': ukurier_login,
                               'id_password': ukurier_password, 'password': ukurier_password,
                               'next': 'http://ukurier.gov.ua/uk/archive/documents/'})
            logging.info('Auth Status: %s' % req.status_code)
            if req.status_code == 200:
                logging.info('\n Autorization on site UKURIER succed... ')
                self.send(['log', '\n Autorization on site UKURIER succed... '])
                last_page = 0
                # Pasring http://ukurier.gov.ua/uk/articles/category/normativni-akti-ministerstv-i-vidomstv/
                HEADER_URL = 'http://ukurier.gov.ua'
                logging.info('Loading 1 site')
                self.send(['log',
                           '\n Loading [http://ukurier.gov.ua/uk/articles/category/normativni-akti-ministerstv-i-vidomstv/]... '])
                req = s.get('http://ukurier.gov.ua/uk/articles/category/normativni-akti-ministerstv-i-vidomstv/')
                soup = Bs(req.text, 'html.parser')
                tag = soup.find('div', attrs={'class': 'pager-body'})
                for child in tag.children:
                    last_page = child.previous_element.string
                last_page = int(last_page)
                end = False
                # For the adding last post
                trigger = True
                for page in range(1, last_page + 1):
                    if end is False:
                        req = s.get(
                            'http://ukurier.gov.ua/uk/articles/category/normativni-akti-ministerstv-i-vidomstv/?page=' + str(
                                page))
                        soup = Bs(req.text, 'html.parser')
                        tag = soup.find('ul', attrs={'class': 'ul-articles-preview'})
                        logging.info('Page %s' % page)
                        for li in tag.find_all('li'):
                            if (HEADER_URL + li.header.h3.a['href']) == LAST_POST[0][0]:
                                end = True
                                break
                            else:
                                if (trigger is True):
                                    new_post = HEADER_URL + li.header.h3.a['href']
                                    trigger = False
                                req = s.get(HEADER_URL + li.header.h3.a['href'])
                                new_tab = Bs(req.text, 'html.parser')
                                article = new_tab.find('article', attrs={'class': 'page'})
                                title = article.header.div.h1.get_text() + article.find('div', attrs={
                                    'class': 'article-body'}).get_text()
                                posts.append(
                                    PostModel(title, hashtags['acts'], (HEADER_URL + li.header.h3.a['href']),
                                              imgs['acts']))
                    else:
                        break
                if new_post != '':
                    LAST_POST[0][0] = new_post
                    new_post = ''
            else:
                self.send(
                    ['log', '\n Autorization on site UKURIER failed...UKURIER won\'t be parsing... '])
        except ConnectionError:
            self.send(['log',
                       '\n Could not load [http://ukurier.gov.ua/uk/articles/category/normativni-akti-ministerstv-i-vidomstv/]'])
        HEADER_URL = 'http://yur-gazeta.com/'
        logging.info('\n Loading [http://yur-gazeta.com/news/]... ')
        # Parsing http://yur-gazeta.com/news/
        self.send(['log',
                   '\n Loading [http://yur-gazeta.com/news/]... '])
        try:
            req = s.get('http://yur-gazeta.com/news/')
            soup = Bs(req.text, 'html.parser')
            end = False
            counter = 0
            # For the adding last post
            trigger = True
            while end is False:
                page = soup.find('a', attrs={'class': 'right'})
                tag = soup.find('ul', attrs={'class': 'materials-date-container'})
                for li in tag.children:
                    if li['class'][0] != 'date-spacer':
                        if li.div.a['href'] != LAST_POST[2][0] and counter <= 10:
                            if trigger is True and li.div.a['href'] != '1' and li.div.a['href'] != 1:
                                new_post = li.div.a['href']
                                trigger = False
                            counter += 1
                            req = s.get(li.div.a['href'])
                            soup = Bs(req.text, 'html.parser')
                            title = soup.find('h1', attrs={'class': 'mat-title'})
                            title = title.get_text() if title is not None else 'oops'
                            article = soup.find('article', attrs={'id': 'material-content'})
                            article = article.get_text() if article is not None else 'oops'
                            posts.append(
                                PostModel(str(title + '.' + article), hashtags['news'], li.div.a['href'], imgs['news']))
                        else:
                            end = True
                            break
                req = s.get(page['href'])
                soup = Bs(req.text, 'html.parser')
            del counter
            if new_post != '' and new_post != '1' and new_post != 1:
                LAST_POST[2][0] = new_post
                new_post = ''
        except ConnectionError:
            self.send(['log',
                       '\n Could not load [http://yur-gazeta.com/news/]'])
        # Parsing http://zakon5.rada.gov.ua/laws/main?user=xml FEEDPARSER
        self.send(['log',
                   '\n  Loading [http://zakon5.rada.gov.ua/laws/main?user=xml]... '])
        del req, soup
        end = False
        # For the adding last post
        trigger = True
        try:
            parser = feedparser.parse('http://zakon5.rada.gov.ua/laws/main?user=xml')
            for item in parser.entries:
                if end is not True:
                    if item.link != LAST_POST[3][0]:
                        if trigger is True:
                            new_post = item.link
                            trigger = False
                        else:
                            posts.append(
                                PostModel(str(item.title + '\n' + item.description), hashtags['laws'], item.link,
                                          imgs['acts']))
                    else:
                        end = True
                else:
                    break
            if new_post != '' and new_post != '1' and new_post != 1:
                LAST_POST[3][0] = new_post
                new_post = ''
            end = False
            # For the adding last post
            trigger = True
        except ConnectionError:
            self.send(['log', '\n Could not load [http://zakon5.rada.gov.ua/laws/main?user=xml]'])

        # Inner function for one common volume parsing
        def expert_parser(url, i):
            nonlocal end, trigger, new_post
            try:
                logging.info('\n  [%s]... ' % url)
                # Parsing http://yur-gazeta.com/news/
                self.send(['log',
                           '\n Loading [%s]... ' % url])
                req = s.get(url)
                soup = Bs(req.text, 'html.parser')
                while end is False:
                    page = soup.find('a', attrs={'class': 'right'})
                    tag = soup.find('ul', attrs={'class': 'material-list imageRight'})
                    for li in tag.children:
                        if li.a['href'] != LAST_POST[i][0]:
                            if li.find('a', attrs={'class': 'title private'}) is None:
                                if trigger is True and li.a['href'] != '1' and li.a['href'] != 1:
                                    new_post = li.a['href']
                                    trigger = False
                                req = s.get(li.a['href'])
                                soup = Bs(req.text, 'html.parser')
                                title = soup.find('h1', attrs={'class': 'mat-title'})
                                title = title.get_text() if title is not None else 'oops'
                                article = soup.find('article', attrs={'id': 'material-content'})
                                article = article.get_text() if article is not None else 'oops'
                                author = soup.find('a', attrs={'class': 'author-name no-link'})
                                author = author.get_text() if author is not None else 'oops'
                                posts.append(
                                    PostModel(str(author + '\n' + title + '.' + article), hashtags['expert'],
                                              li.a['href']
                                              , imgs['expert']))
                        else:
                            end = True
                            break
                    req = s.get(page['href']) if page is not None else req
                    soup = Bs(req.text, 'html.parser')
            except ConnectionError:
                self.send(['log', '\n Could not load [%s]' % url])
            end = False
            # For the adding last post
            trigger = True
            if new_post != '' and new_post != '1' and new_post != 1:
                LAST_POST[i][0] = new_post
                new_post = ''

        EXPERTS = ['http://yur-gazeta.com/publications/practice/sudova-praktika/',
                   'http://yur-gazeta.com/publications/practice/korporativne-pravo-ma/',
                   'http://yur-gazeta.com/publications/practice/neruhomist-ta-budivnictvo/',
                   'http://yur-gazeta.com/publications/practice/bankivske-ta-finansove-pravo/',
                   'http://yur-gazeta.com/publications/practice/antimonopolne-konkurentne-pravo/',
                   'http://yur-gazeta.com/publications/practice/zemelne-agrarne-pravo/',
                   'http://yur-gazeta.com/publications/practice/podatkova-praktika/',
                   'http://yur-gazeta.com/publications/practice/zahist-intelektualnoyi-vlasnosti-avtorske-pravo/',
                   'http://yur-gazeta.com/publications/practice/mizhnarodniy-arbitrazh-ta-adr/',
                   'http://yur-gazeta.com/publications/practice/mizhnarodne-pravo-investiciyi/',
                   'http://yur-gazeta.com/publications/practice/bankrutstvo-i-restrukturizaciya/',
                   'http://yur-gazeta.com/publications/practice/morske-pravo/',
                   'http://yur-gazeta.com/publications/practice/medichne-pravo-farmacevtika/',
                   'http://yur-gazeta.com/publications/practice/vikonavche-provadzhennya/',
                   'http://yur-gazeta.com/publications/practice/trudove-pravo/',
                   'http://yur-gazeta.com/publications/practice/kriminalne-pravo-ta-proces/',
                   'http://yur-gazeta.com/publications/practice/simeyne-pravo/',
                   'http://yur-gazeta.com/publications/practice/gospodarske-pravo/',
                   'http://yur-gazeta.com/publications/practice/zovnishnoekonomichna-diyalnist/',
                   'http://yur-gazeta.com/publications/practice/povitryane-ta-aviaciyne-pravo/',
                   'http://yur-gazeta.com/publications/practice/informaciyne-pravo-telekomunikaciyi/',
                   'http://yur-gazeta.com/publications/practice/civilne-pravo/',
                   'http://yur-gazeta.com/publications/practice/mitne-pravo/',
                   'http://yur-gazeta.com/publications/practice/cinni-paperi-ta-fondoviy-rinok/',
                   'http://yur-gazeta.com/publications/practice/ekologichne-pravo-turistichne-pravo/',
                   'http://yur-gazeta.com/publications/practice/derzhavnoprivatne-partnerstvo/',
                   'http://yur-gazeta.com/publications/practice/energetichne-pravo/',
                   'http://yur-gazeta.com/publications/practice/sportivne-pravo/',
                   'http://yur-gazeta.com/publications/practice/transportne-pravo/',
                   'http://yur-gazeta.com/publications/practice/inshe/']
        index = 4  # Index in last posts file
        for url in EXPERTS:
            # print('URL: %s' % url)
            expert_parser(url, index)
            index += 1
        ######## http://protokol.com.ua/
        HEADER_URL = 'http://protokol.com.ua/'
        logging.info('\n Loading [http://protokol.com.ua/ua/yruduchna_duskysiya/]... ')
        # Parsing http://protokol.com.ua/ua/yruduchna_duskysiya/
        self.send(['log',
                   '\n Loading [http://protokol.com.ua/ua/yruduchna_duskysiya/]... '])

        try:
            req = s.get('http://protokol.com.ua/ua/yruduchna_duskysiya/')
            soup = Bs(req.text, 'html.parser')
            page = soup.find('div', attrs={'class': 'pagination'})
            page = page.find_all('a')
            page = int(page[-1].get_text())
            for p in range(1, page):
                if end is False:
                    req = s.get('http://protokol.com.ua/ua/yruduchna_duskysiya/' + str(p))
                    soup = Bs(req.text, 'html.parser')
                    tag = soup.find('div', attrs={'id': 'main_content'})
                    for child in tag.find_all('div', attrs={'class': 'article'}):
                        if HEADER_URL + child.a['href'] != LAST_POST[34][0]:
                            if trigger is True:
                                new_post = HEADER_URL + child.a['href']
                                trigger = False
                            title = child.a.get_text()
                            req = s.get(HEADER_URL + child.a['href'])
                            soup = Bs(req.text, 'html.parser')
                            page = soup.find('div', attrs={'class': 'description'})
                            article = page.get_text() if page is not None else 'oops'
                            posts.append(PostModel(title + '.' + article, hashtags['expert_protokol'],
                                                   HEADER_URL + child.a['href'], imgs['expert']))
                        else:
                            end = True
                            break
                else:
                    break
            if new_post != '' and new_post != '1' and new_post != 1:
                LAST_POST[34][0] = new_post
                new_post = ''
            end = False
            # For the adding last post
            trigger = True
        except ConnectionError:
            logging.error('\n Error: [{}] : [{}]'.format(sys.exc_info()[0], sys.exc_info()[1]))
            self.send(['log',
                       '\n Could not load [http://protokol.com.ua/ua/yruduchna_duskysiya/]... '])
        self.write(LAST_POST)
        None if posts else self.send(['log', '\n New post didn\'t add , nothing to load...'])
        self.send(['log', '\n All sites loading done...'])
        t1 = time.time() - t0
        t1 = int(t1)
        self.send(['log', 'Time expired: %s sec' % t1])
        self.cond(posts)


################################################
class PostUploader:
    def __init__(self, conn=None, posts=None, ready=None):
        self.conn = conn  # Link update_text func in VpmRoot
        self.posts = copy.deepcopy(posts)
        self.ready = ready  # Link ready func in VpmRoot
        self.owner_id = '-94269795'  # Id of public page

    # Sending log text via update_text func in VpmRoot
    def send(self, message):
        self.conn(message)

    # Try to authorizate in vk
    def auth_vk(self):
        try:
            self.send('\n Authorizaton vkontakte...')
            self.session = vk.AuthSession(app_id='5502504', user_login=globals()['VK_LOGIN'],
                                          user_password=globals()['VK_PASSWORD'], scope='wall')
            self.api = vk.API(self.session, v='5.52', lang='ua', timeout=10)
            self.send('\n Authorizaton vkontakte succed...')
            self.upload_post()

        except ConnectionError:
            self.send('\n Error: [{}] : [{}]'.format(sys.exc_info()[0], sys.exc_info()[1]))

    # Actually upload post to vk
    def upload_post(self):
        try:
            iterator = random.randrange(len(self.posts))
            self.api.wall.post(owner_id=self.owner_id, message=str(
                self.posts[iterator].get_hashtag() + '\n' + self.posts[iterator].get_post() + '\n' + self.posts[
                    iterator].get_link()), attachment=self.posts[iterator].get_img())
            removed = self.posts.pop(iterator)
            self.send('\n Post %s from %s uploaded on wall...\n Next uploading in 1 min... ' % (
                iterator, len(self.posts)))
        except ConnectionError:
            self.send('\n Error: [{}] : [{}]'.format(sys.exc_info()[0], sys.exc_info()[1]))
            self.send('\n Next uploading in 1 min... ')
        if len(self.posts) != 0:
            time.sleep(60)
            self.upload_post()
        else:
            self.send('\n All post uploaded...')
            self.ready()

    # Func that start auth in vk
    def send_posts(self):
        self.send('\n Preparing done...')
        self.auth_vk()


################################################
if __name__ == '__main__':
    logging.info('App has run')
    print('VERSION %s' % VERSION)
    VpmApp().run()
else:
    logging.info('Oops this is not main script!')
