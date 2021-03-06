#Embedded file name: ACEStream\Core\Overlay\OverlayApps.pyo
from MetadataHandler import MetadataHandler
from threading import Lock
from threading import currentThread
from time import time
from traceback import print_exc
import sys
from ACEStream.Core.BitTornado.BT1.MessageID import *
from ACEStream.Core.BuddyCast.buddycast import BuddyCastFactory
from ACEStream.Core.ProxyService.CoordinatorMessageHandler import CoordinatorMessageHandler
from ACEStream.Core.ProxyService.HelperMessageHandler import HelperMessageHandler
from ACEStream.Core.NATFirewall.DialbackMsgHandler import DialbackMsgHandler
from ACEStream.Core.NATFirewall.NatCheckMsgHandler import NatCheckMsgHandler
from ACEStream.Core.SocialNetwork.FriendshipMsgHandler import FriendshipMsgHandler
from ACEStream.Core.SocialNetwork.RemoteQueryMsgHandler import RemoteQueryMsgHandler
from ACEStream.Core.SocialNetwork.RemoteTorrentHandler import RemoteTorrentHandler
from ACEStream.Core.SocialNetwork.SocialNetworkMsgHandler import SocialNetworkMsgHandler
from ACEStream.Core.Statistics.Crawler import Crawler
from ACEStream.Core.Statistics.DatabaseCrawler import DatabaseCrawler
from ACEStream.Core.Statistics.FriendshipCrawler import FriendshipCrawler
from ACEStream.Core.Statistics.SeedingStatsCrawler import SeedingStatsCrawler
from ACEStream.Core.Statistics.VideoPlaybackCrawler import VideoPlaybackCrawler
from ACEStream.Core.Statistics.RepexCrawler import RepexCrawler
from ACEStream.Core.Statistics.PunctureCrawler import PunctureCrawler
from ACEStream.Core.Statistics.ChannelCrawler import ChannelCrawler
from ACEStream.Core.Statistics.UserEventLogCrawler import UserEventLogCrawler
from ACEStream.Core.Utilities.utilities import show_permid_short
from ACEStream.Core.simpledefs import *
from ACEStream.Core.Subtitles.SubtitlesHandler import SubtitlesHandler
from ACEStream.Core.Subtitles.SubtitlesSupport import SubtitlesSupport
from ACEStream.Core.Subtitles.PeerHaveManager import PeersHaveManager
DEBUG = False

class OverlayApps:
    __single = None

    def __init__(self):
        if OverlayApps.__single:
            raise RuntimeError, 'OverlayApps is Singleton'
        OverlayApps.__single = self
        self.coord_handler = None
        self.help_handler = None
        self.metadata_handler = None
        self.buddycast = None
        self.collect = None
        self.dialback_handler = None
        self.socnet_handler = None
        self.rquery_handler = None
        self.chquery_handler = None
        self.friendship_handler = None
        self.msg_handlers = {}
        self.connection_handlers = []
        self.text_mode = None
        self.requestPolicyLock = Lock()

    def getInstance(*args, **kw):
        if OverlayApps.__single is None:
            OverlayApps(*args, **kw)
        return OverlayApps.__single

    getInstance = staticmethod(getInstance)

    def register(self, overlay_bridge, session, launchmany, config, requestPolicy):
        self.overlay_bridge = overlay_bridge
        self.launchmany = launchmany
        self.requestPolicy = requestPolicy
        self.text_mode = config.has_key('text_mode')
        overlay_bridge.register_recv_callback(self.handleMessage)
        overlay_bridge.register_conns_callback(self.handleConnection)
        i_am_crawler = False
        if config['crawler']:
            crawler = Crawler.get_instance(session)
            self.register_msg_handler([CRAWLER_REQUEST], crawler.handle_request)
            database_crawler = DatabaseCrawler.get_instance()
            crawler.register_message_handler(CRAWLER_DATABASE_QUERY, database_crawler.handle_crawler_request, database_crawler.handle_crawler_reply)
            seeding_stats_crawler = SeedingStatsCrawler.get_instance()
            crawler.register_message_handler(CRAWLER_SEEDINGSTATS_QUERY, seeding_stats_crawler.handle_crawler_request, seeding_stats_crawler.handle_crawler_reply)
            friendship_crawler = FriendshipCrawler.get_instance(session)
            crawler.register_message_handler(CRAWLER_FRIENDSHIP_STATS, friendship_crawler.handle_crawler_request, friendship_crawler.handle_crawler_reply)
            natcheck_handler = NatCheckMsgHandler.getInstance()
            natcheck_handler.register(launchmany)
            crawler.register_message_handler(CRAWLER_NATCHECK, natcheck_handler.gotDoNatCheckMessage, natcheck_handler.gotNatCheckReplyMessage)
            crawler.register_message_handler(CRAWLER_NATTRAVERSAL, natcheck_handler.gotUdpConnectRequest, natcheck_handler.gotUdpConnectReply)
            videoplayback_crawler = VideoPlaybackCrawler.get_instance()
            crawler.register_message_handler(CRAWLER_VIDEOPLAYBACK_EVENT_QUERY, videoplayback_crawler.handle_event_crawler_request, videoplayback_crawler.handle_event_crawler_reply)
            crawler.register_message_handler(CRAWLER_VIDEOPLAYBACK_INFO_QUERY, videoplayback_crawler.handle_info_crawler_request, videoplayback_crawler.handle_info_crawler_reply)
            repex_crawler = RepexCrawler.get_instance(session)
            crawler.register_message_handler(CRAWLER_REPEX_QUERY, repex_crawler.handle_crawler_request, repex_crawler.handle_crawler_reply)
            puncture_crawler = PunctureCrawler.get_instance()
            crawler.register_message_handler(CRAWLER_PUNCTURE_QUERY, puncture_crawler.handle_crawler_request, puncture_crawler.handle_crawler_reply)
            channel_crawler = ChannelCrawler.get_instance()
            crawler.register_message_handler(CRAWLER_CHANNEL_QUERY, channel_crawler.handle_crawler_request, channel_crawler.handle_crawler_reply)
            usereventlog_crawler = UserEventLogCrawler.get_instance()
            crawler.register_message_handler(CRAWLER_USEREVENTLOG_QUERY, usereventlog_crawler.handle_crawler_request, usereventlog_crawler.handle_crawler_reply)
            if crawler.am_crawler():
                i_am_crawler = True
                self.register_msg_handler([CRAWLER_REPLY], crawler.handle_reply)
                self.register_connection_handler(crawler.handle_connection)
                if 'database' in sys.argv:
                    crawler.register_crawl_initiator(database_crawler.query_initiator)
                if 'videoplayback' in sys.argv:
                    crawler.register_crawl_initiator(videoplayback_crawler.query_initiator)
                if 'seedingstats' in sys.argv:
                    crawler.register_crawl_initiator(seeding_stats_crawler.query_initiator, frequency=1800)
                if 'friendship' in sys.argv:
                    crawler.register_crawl_initiator(friendship_crawler.query_initiator)
                if 'natcheck' in sys.argv:
                    crawler.register_crawl_initiator(natcheck_handler.doNatCheck, 3600)
                if 'repex' in sys.argv:
                    crawler.register_crawl_initiator(repex_crawler.query_initiator)
                if 'puncture' in sys.argv:
                    crawler.register_crawl_initiator(puncture_crawler.query_initiator)
                if 'channel' in sys.argv:
                    crawler.register_crawl_initiator(channel_crawler.query_initiator)
                if 'usereventlog' in sys.argv:
                    crawler.register_crawl_initiator(usereventlog_crawler.query_initiator)
        else:
            self.register_msg_handler([CRAWLER_REQUEST, CRAWLER_REPLY], self.handleDisabledMessage)
        self.metadata_handler = MetadataHandler.getInstance()
        if config['download_help']:
            self.coord_handler = CoordinatorMessageHandler(launchmany)
            self.register_msg_handler(HelpHelperMessages, self.coord_handler.handleMessage)
            self.help_handler = HelperMessageHandler()
            self.help_handler.register(session, self.metadata_handler, config['download_help_dir'], config.get('coopdlconfig', False))
            self.register_msg_handler(HelpCoordinatorMessages, self.help_handler.handleMessage)
        self.metadata_handler.register(overlay_bridge, self.help_handler, launchmany, config)
        self.register_msg_handler(MetadataMessages, self.metadata_handler.handleMessage)
        config['subtitles_collecting'] = False
        if not config['subtitles_collecting']:
            self.subtitles_handler = None
        else:
            self.subtitles_handler = SubtitlesHandler.getInstance()
            self.subtitles_handler.register(self.overlay_bridge, self.launchmany.richmetadataDbHandler, self.launchmany.session)
            self.peersHaveManger = PeersHaveManager.getInstance()
            if not self.peersHaveManger.isRegistered():
                self.peersHaveManger.register(self.launchmany.richmetadataDbHandler, self.overlay_bridge)
            self.subtitle_support = SubtitlesSupport.getInstance()
            keypair = self.launchmany.session.keypair
            permid = self.launchmany.session.get_permid()
            self.subtitle_support._register(self.launchmany.richmetadataDbHandler, self.subtitles_handler, self.launchmany.channelcast_db, permid, keypair, self.peersHaveManger, self.overlay_bridge)
            self.subtitle_support.runDBConsinstencyRoutine()
        if not config['torrent_collecting']:
            self.torrent_collecting_solution = 0
        else:
            self.torrent_collecting_solution = config['buddycast_collecting_solution']
        if config['buddycast']:
            self.buddycast = BuddyCastFactory.getInstance(superpeer=config['superpeer'], log=config['overlay_log'])
            self.buddycast.register(overlay_bridge, launchmany, launchmany.rawserver_fatalerrorfunc, self.metadata_handler, self.torrent_collecting_solution, config['start_recommender'], config['buddycast_max_peers'], i_am_crawler)
            self.register_msg_handler(BuddyCastMessages, self.buddycast.handleMessage)
            self.register_connection_handler(self.buddycast.handleConnection)
        if config['dialback']:
            self.dialback_handler = DialbackMsgHandler.getInstance()
            self.dialback_handler.register(overlay_bridge, launchmany, launchmany.rawserver, config)
            self.register_msg_handler([DIALBACK_REQUEST], self.dialback_handler.olthread_handleSecOverlayMessage)
            self.register_connection_handler(self.dialback_handler.olthread_handleSecOverlayConnection)
        else:
            self.register_msg_handler([DIALBACK_REQUEST], self.handleDisabledMessage)
        if config['socnet']:
            self.socnet_handler = SocialNetworkMsgHandler.getInstance()
            self.socnet_handler.register(overlay_bridge, launchmany, config)
            self.register_msg_handler(SocialNetworkMessages, self.socnet_handler.handleMessage)
            self.register_connection_handler(self.socnet_handler.handleConnection)
            self.friendship_handler = FriendshipMsgHandler.getInstance()
            self.friendship_handler.register(overlay_bridge, launchmany.session)
            self.register_msg_handler(FriendshipMessages, self.friendship_handler.handleMessage)
            self.register_connection_handler(self.friendship_handler.handleConnection)
        if config['rquery']:
            self.rquery_handler = RemoteQueryMsgHandler.getInstance()
            self.rquery_handler.register(overlay_bridge, launchmany, config, self.buddycast, log=config['overlay_log'])
            self.register_msg_handler(RemoteQueryMessages, self.rquery_handler.handleMessage)
            self.register_connection_handler(self.rquery_handler.handleConnection)
        if config['subtitles_collecting']:
            hndl = self.subtitles_handler.getMessageHandler()
            self.register_msg_handler(SubtitleMessages, hndl)
        if config['torrent_collecting']:
            self.rtorrent_handler = RemoteTorrentHandler.getInstance()
            self.rtorrent_handler.register(overlay_bridge, self.metadata_handler, session)
            self.metadata_handler.register2(self.rtorrent_handler)
        self.register_connection_handler(self.notifier_handles_connection)
        if config['buddycast']:
            self.buddycast.register2()

    def early_shutdown(self):
        if self.friendship_handler is not None:
            self.friendship_handler.shutdown()

    def register_msg_handler(self, ids, handler):
        for id in ids:
            if DEBUG:
                print >> sys.stderr, 'olapps: Message handler registered for', getMessageName(id)
            self.msg_handlers[id] = handler

    def register_connection_handler(self, handler):
        if DEBUG:
            print >> sys.stderr, 'olapps: Connection handler registered for', handler
        self.connection_handlers.append(handler)

    def handleMessage(self, permid, selversion, message):
        if not self.requestAllowed(permid, message[0]):
            if DEBUG:
                print >> sys.stderr, 'olapps: Message not allowed', getMessageName(message[0])
            return False
        if message[0] in self.msg_handlers:
            id_ = message[0]
        else:
            if DEBUG:
                print >> sys.stderr, 'olapps: No handler found for', getMessageName(message[0:2])
            return False
        if DEBUG:
            print >> sys.stderr, 'olapps: handleMessage', getMessageName(id_), 'v' + str(selversion)
        try:
            if DEBUG:
                st = time()
                ret = self.msg_handlers[id_](permid, selversion, message)
                et = time()
                diff = et - st
                if diff > 0:
                    print >> sys.stderr, 'olapps: ', getMessageName(id_), 'returned', ret, 'TOOK %.5f' % diff
                return ret
            return self.msg_handlers[id_](permid, selversion, message)
        except:
            print_exc()
            return False

    def handleDisabledMessage(self, *args):
        return True

    def handleConnection(self, exc, permid, selversion, locally_initiated):
        if DEBUG:
            print >> sys.stderr, 'olapps: handleConnection', exc, selversion, locally_initiated, currentThread().getName()
        for handler in self.connection_handlers:
            try:
                handler(exc, permid, selversion, locally_initiated)
            except:
                print >> sys.stderr, 'olapps: Exception during connection handler calling'
                print_exc()

    def requestAllowed(self, permid, messageType):
        self.requestPolicyLock.acquire()
        try:
            rp = self.requestPolicy
        finally:
            self.requestPolicyLock.release()

        allowed = rp.allowed(permid, messageType)
        if DEBUG:
            if allowed:
                word = 'allowed'
            else:
                word = 'denied'
            print >> sys.stderr, 'olapps: Request type %s from %s was %s' % (getMessageName(messageType), show_permid_short(permid), word)
        return allowed

    def setRequestPolicy(self, requestPolicy):
        self.requestPolicyLock.acquire()
        try:
            self.requestPolicy = requestPolicy
        finally:
            self.requestPolicyLock.release()

    def notifier_handles_connection(self, exc, permid, selversion, locally_initiated):
        self.launchmany.session.uch.notify(NTFY_PEERS, NTFY_CONNECTION, permid, True)
