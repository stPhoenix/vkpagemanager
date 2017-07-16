import sys
import pytest
import os.path as op
from functools import partial
from kivy.clock import Clock

main_path = op.dirname(op.dirname(op.abspath(__file__)))
sys.path.append(main_path)

from vkpagemanager import VpmApp, PostModel


class TestVpmRoot:

    app = VpmApp()

    def test_start(self):
        p = partial(self.app.stop)
        Clock.schedule_once(p, 1)
        self.app.run()

    def test_init(self):
        assert len(self.app.root.ids.loglabel.text) > 0
        assert self.app.root.ids.sendButton.disabled is True
        assert self.app.root.posts == []
        assert self.app.root.send_posts == []
        assert self.app.root.reload_timer is False
        assert self.app.root.COUNTER == 60
        assert self.app.root.reload_counter == 60
        assert self.app.root.auto_pilot is False

    @pytest.mark.skip(reason="something that I didn't found out yet")
    def test_update_text(self):
        text = 'Some text'
        self.app.root.update_text(text)
        assert text in self.app.root.ids.loglabel.text

    def test_reload_text(self):
        self.app.root.reload_counter = 1
        self.app.root.reload_text(0)
        assert self.app.root.reload_counter == 0
        assert '0' in self.app.root.ids.rLabel.text

    def test_runt(self):
        self.app.root.runt()
        assert self.app.root.ids.pLayout.disabled is False
        assert self.app.root.ids.startButton.disabled is True
        assert self.app.root.ids.spinner.active is True

    def test_ready(self):
        self.app.root.ready()
        Clock.unschedule(self.app.root.reload_timer)
        assert 'Reload in 60m' in self.app.root.ids.rLabel.text
        assert self.app.root.ids.pLayout.children == []

    def test_show_posts(self):
        posts = []
        for i in range(10):
            posts.append(PostModel(p='text.text', h='#text'))
        self.app.root.posts = posts
        self.app.root.show_posts()




