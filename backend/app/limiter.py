"""Rate limiting — protects sensitive endpoints from brute-force attacks.

Limits are counted in memory, per pod, with no shared store like Redis: with
more than one backend replica each pod counts independently, so the
effective cluster-wide limit is multiplied by roughly the replica count.
The limits below are chosen low enough (5-10/minute) that even tripled —
this chart is meant for a handful of replicas, not dozens — brute-forcing a
password or spamming registrations/emails is still impractical. Add a
shared store if you ever need replicas at real scale.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
