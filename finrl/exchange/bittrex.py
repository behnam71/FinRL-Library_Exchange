""" Bittrex exchange subclass """
import logging
from typing import Dict

from finrl.exchange import Exchange

logger = logging.getLogger(__name__)


class Bittrex(Exchange):
    """
    Bittrex exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.
    Please note that this exchange is not included in the list of exchanges
    officially supported by the Freqtrade development team. So some features
    may still not work as expected.
    """
    _ft_has: Dict = {"l2_limit_range": [1, 25, 500],
                    }
