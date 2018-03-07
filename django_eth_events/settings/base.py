# ------------------------------------------------------------------------------
# ETHEREUM CONFIGURATION
# ------------------------------------------------------------------------------
# If IPC_PATH is set, ETHEREUM_NODE_HOST and ETHEREUM_NODE_PORT are not used
# ETHEREUM_IPC_PATH = 'path/to/ipc'
ETHEREUM_NODE_HOST = 'https://mainnet.infura.io'
ETHEREUM_NODE_PORT = 8545
ETHEREUM_NODE_SSL = 1
ETHEREUM_MAX_WORKERS = 10

# ------------------------------------------------------------------------------
# CELERY CONFIGURATION
# ------------------------------------------------------------------------------
# BROKER_URL = 'django://'
BROKER_POOL_LIMIT = 1
BROKER_CONNECTION_TIMEOUT = 10

# Celery configuration
CELERY_RESULT_SERIALIZER = 'json'
# configure queues, currently we have only one
CELERY_DEFAULT_QUEUE = 'default'

# Sensible settings for celery
CELERY_ALWAYS_EAGER = False
CELERY_ACKS_LATE = True
CELERY_TASK_PUBLISH_RETRY = True
CELERY_DISABLE_RATE_LIMITS = False

# By default we will ignore result
# If you want to see results and try out tasks interactively, change it to False
# Or change this setting on tasks level
CELERY_IGNORE_RESULT = False
CELERY_SEND_TASK_ERROR_EMAILS = False
CELERY_TASK_RESULT_EXPIRES = 600
# Don't use pickle as serializer, json is much safer
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ['application/json']
CELERYD_HIJACK_ROOT_LOGGER = False
CELERYD_PREFETCH_MULTIPLIER = 1
CELERYD_MAX_TASKS_PER_CHILD = 1000
CELERY_LOCK_EXPIRE = 60  # 1 minute

# ------------------------------------------------------------------------------
# IPFS CONFIGURATION
# ------------------------------------------------------------------------------
IPFS_HOST = 'http://ipfs.infura.io'
IPFS_PORT = 5001

ETH_EVENTS = []
