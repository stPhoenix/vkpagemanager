from distutils.core import setup

setup(
    name='vkpagemanager',
    version='1.1.7',
    packages=['vkpagemanager'],
    url='https://github.com/stPhoenix/vkpageamanager',
    license='GNU General Public License v3.0',
    author='bohdan sapovsky',
    author_email='bohdansapovsky@gmail.com',
    description='VK Page Manager - script for automatic parcing news sites and rss. Parced news uploading # into vkontakte public page using api in vk library',
    requires=['kivy', 'bs4', 'vk', 'feedparser']
)
