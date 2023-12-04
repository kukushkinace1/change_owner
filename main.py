import asyncio
import time
import random

from sys import stderr
from tqdm import tqdm
from loguru import logger
from starknet_py.contract import Contract
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.hash.utils import compute_hash_on_elements, message_signature
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.account.account import Account
from starknet_py.net.models import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair

with open('address.txt', 'r') as proxy_file:
    addresses = [line.strip() for line in proxy_file]
with open('new_private_key.txt', 'r') as proxy_file:
    new_private_key = [line.strip() for line in proxy_file]
with open('old_private_key.txt', 'r') as proxy_file:
    old_private_key = [line.strip() for line in proxy_file]

logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white> | <level>{level: <3}</level> | <level>{message}</level>")


async def main():
    if len(addresses) != len(new_private_key) and len(addresses) != len(old_private_key):
        print('Количество строк в файлах разное!')
        return
    else:
        wal_data = list(zip(addresses, new_private_key, old_private_key))

    max_acc = len(addresses)
    current_acc = 0

    for address, new_key, old_key in wal_data:
        current_acc += 1
        try:
            client = FullNodeClient("https://starknet-mainnet.public.blastapi.io")

            old_key = int(old_key, 0)
            new_key = int(new_key, 0)
            address = int(address, 0)

            old_key_pair = KeyPair.from_private_key(old_key)
            new_key_pair = KeyPair.from_private_key(new_key)

            old_account = Account(
                        address=address,
                        client=client,
                        key_pair=old_key_pair,
                        chain=StarknetChainId.MAINNET,
                    )

            messageHash = compute_hash_on_elements([
              get_selector_from_name("change_owner"),
              StarknetChainId.MAINNET,
              address,
              old_key_pair.public_key,
            ])
            r, s = message_signature(messageHash, new_key_pair.private_key)

            contract = await Contract.from_address(address=address, provider=old_account)
            call = contract.functions['change_owner'].prepare(
                new_key_pair.public_key, r, s
            )
            transaction = await old_account.sign_invoke_transaction(
                calls=[call, ],
                auto_estimate=True,
                nonce=await old_account.get_nonce()
            )

            transaction_response = await old_account.client.send_transaction(transaction)
            await old_account.client.wait_for_tx(transaction_response.transaction_hash, check_interval=10)
            logger.info(f'[{current_acc}/{max_acc}] [{hex(address)}] сменил приватник')
            logger.info(f'https://starkscan.co/tx/{hex(transaction_response.transaction_hash)}')
        except Exception as e:
            logger.error(f"Ошибка | {e}")

        sleeping(10, 20)


def sleeping(ot, do):
    x = random.randint(ot, do)
    for _ in tqdm(range(x), desc='sleep ', bar_format='{desc}: {n_fmt}/{total_fmt}'):
        time.sleep(1)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())