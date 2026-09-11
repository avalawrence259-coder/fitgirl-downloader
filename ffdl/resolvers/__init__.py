"""
ffdl.resolvers Package
"""

from .dispatcher import URLDispatcher
from .fuckingfast import FuckingFastResolver
from .fitgirl_scraper import FitGirlPageScraper
from .privatebin import PrivateBinDecryptor
from .torrent import TorrentResolver
from .datanodes import DirectHostResolver
from .cloud_fallback import FirecrawlClient

__all__ = [
    "URLDispatcher",
    "FuckingFastResolver",
    "FitGirlPageScraper",
    "PrivateBinDecryptor",
    "TorrentResolver",
    "DirectHostResolver",
    "FirecrawlClient",
]
