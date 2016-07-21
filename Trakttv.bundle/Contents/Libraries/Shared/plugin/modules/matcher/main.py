from plugin.core.cache import CacheManager
from plugin.core.enums import MatcherMode
from plugin.modules.core.base import Module
from plugin.preferences import Preferences

from plex import Plex
from plex.objects.library.metadata.episode import Episode
import plex_database.matcher
import plex_metadata.matcher
import logging

log = logging.getLogger(__name__)


class Matcher(Module):
    __key__ = 'matcher'

    def __init__(self):
        self._cache = None

        self._database_matcher = None
        self._metadata_matcher = None

    @property
    def database(self):
        return self._database_matcher

    @property
    def metadata(self):
        return self._metadata_matcher

    def configure(self):
        extended = Preferences.get('matcher.mode') == MatcherMode.PlexExtended

        # Configure matchers
        matchers = [
            self._database_matcher,
            self._metadata_matcher,

            # Default matchers
            plex_database.matcher.Default,
            plex_metadata.matcher.Default
        ]

        for matcher in matchers:
            # Update cache
            matcher.cache = self._cache

            # Configure features
            if matcher.caper_enabled != extended or matcher.extend_enabled != extended:
                matcher.caper_enabled = extended
                matcher.extend_enabled = extended

                log.info('Extended matcher has been %s on %r', 'enabled' if extended else 'disabled', matcher)

        return True

    def process(self, episode):
        if not episode or not isinstance(episode, Episode):
            raise ValueError('Invalid value specified for the "episode" parameter: %r' % (episode,))

        if not self._metadata_matcher:
            return episode.season.index, [episode.index]

        # Process episode with matcher
        season, episodes = self._metadata_matcher.process(episode)

        log.debug('Matcher returned season: %r, episodes: %r', season, episodes)
        return season, episodes

    def start(self):
        if self._database_matcher and self._metadata_matcher:
            return

        if self._database_matcher is False or self._metadata_matcher is False:
            return

        try:
            self._cache = CacheManager.get('plex.matcher')

            self._database_matcher = plex_database.matcher.Matcher(self._cache, Plex.client)
            self._metadata_matcher = plex_metadata.matcher.Matcher(self._cache, Plex.client)
        except Exception, ex:
            log.warn('Unable to initialize matchers: %s', ex, exc_info=True)

            # Mark attributes as disabled
            self._cache = False
            self._database_matcher = False
            self._metadata_matcher = False
            return

        # Configure matchers
        self.configure()
