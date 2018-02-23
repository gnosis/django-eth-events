from .exceptions import (NetworkReorgException, NoBackupException,
                         UnknownBlockReorgException, Web3ConnectionException)
from .models import Block, Daemon
from .utils import remove_0x_head
from .web3_service import Web3Service


def check_reorg(provider=None):
    """
    Checks for reorgs to happening
    :param provider: optional Web3 provider instance
    :return: Tuple (True|False, None|Block number)
    :raise NetworkReorgException
    :raise UnknownBlockReorg
    :raise NoBackup
    """
    saved_block_number = Daemon.get_solo().block_number

    web3 = None
    try:
        web3 = Web3Service(provider=provider).web3
        current_block_number = web3.eth.blockNumber
    except:
        if not web3.isConnected():
            raise Web3ConnectionException('Web3 provider is not connected')
        else:
            raise NetworkReorgException('Unable to get block number from current node. Check the node is up and running.')

    if current_block_number >= saved_block_number:
        # check last saved block hash haven't changed
        blocks = Block.objects.all().order_by('-block_number')
        if blocks.count():
            # check if there was reorg
            for block in blocks:
                try:
                    node_block_hash = remove_0x_head(web3.eth.getBlock(block.block_number)['hash'])
                except:
                    raise UnknownBlockReorgException
                if block.block_hash == node_block_hash:
                    # if is last saved block, no reorg
                    if block.block_number == saved_block_number:
                        return False, None
                    else:
                        # there was a reorg from a saved block, we can do rollback
                        return True, block.block_number

            # Exception, no saved history enough
            errors = {
                'saved_block_number': saved_block_number,
                'current_block_number': current_block_number,
                'las_saved_block_hash': blocks[0].block_hash
            }
            raise NoBackupException(message='Not enough backup blocks, reorg cannot be rollback', errors=errors)

        else:
            # No backup data
            return False, None
    else:
        # check last common block hash haven't changed
        blocks = Block.objects.filter(block_number__lte=current_block_number).order_by('-block_number')
        if blocks.count():
            # check if there was reorg
            for block in blocks:
                try:
                    node_block_hash = remove_0x_head(web3.eth.getBlock(block.block_number)['hash'])
                except:
                    raise UnknownBlockReorgException
                if block.block_hash == node_block_hash:
                    # if is last saved block, no reorg
                    if block.block_number == saved_block_number:
                        return False, None
                    else:
                        # there was a reorg from a saved block, we can do rollback
                        return True, block.block_number

            # Exception, no saved history enough
            errors = {
                'saved_block_number': saved_block_number,
                'current_block_number': current_block_number,
                'las_saved_block_hash': blocks[0].block_hash
            }
            raise NoBackupException(message='Not enough backup blocks, reorg cannot be rollback', errors=errors)
        else:
            # No backup data
            return False, None
