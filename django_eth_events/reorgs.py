from .exceptions import NoBackupException, UnknownBlockReorgException
from .models import Block
from .utils import remove_0x_head
from .web3_service import Web3Service


def check_reorg(daemon_block_number, current_block_number=None, provider=None):
    """
    Checks if reorgs are happening
    :param daemon_block_number: daemon database block_number
    :param current_block_number: current block_number
    :param provider: optional Web3 provider instance
    :return: Tuple (True|False, None|Block number)
    :raise Web3ConnectionException
    :raise UnknownBlockReorg
    :raise NoBackup
    """
    web3_service = Web3Service(provider=provider)
    current_block_number = current_block_number if current_block_number else web3_service.get_current_block_number()

    if current_block_number >= daemon_block_number:
        # check last saved block hash haven't changed
        blocks = Block.objects.all().order_by('-block_number')
        if blocks.count():
            # check if there was reorg
            for block in blocks:
                try:
                    node_block_hash = remove_0x_head(web3_service.get_block(block.block_number)['hash'])
                except:
                    raise UnknownBlockReorgException
                if block.block_hash == node_block_hash:
                    # if is last saved block, no reorg
                    if block.block_number == daemon_block_number:
                        return False, None
                    else:
                        # there was a reorg from a saved block, we can do rollback
                        return True, block.block_number

            # Exception, no saved history enough
            errors = {
                'daemon_block_number': daemon_block_number,
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
                    node_block_hash = remove_0x_head(web3_service.get_block(block.block_number)['hash'])
                except:
                    raise UnknownBlockReorgException
                if block.block_hash == node_block_hash:
                    # if is last saved block, no reorg
                    if block.block_number == daemon_block_number:
                        return False, None
                    else:
                        # there was a reorg from a saved block, we can do rollback
                        return True, block.block_number

            # Exception, no saved history enough
            errors = {
                'daemon_block_number': daemon_block_number,
                'current_block_number': current_block_number,
                'las_saved_block_hash': blocks[0].block_hash
            }
            raise NoBackupException(message='Not enough backup blocks, reorg cannot be rolled back', errors=errors)
        else:
            # No backup data
            return False, None
