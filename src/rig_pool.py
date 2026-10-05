"""Manages a pool of shared, SIMULATED infotainment test rigs.

Models remote access to shared test setups — multiple users share a
limited pool of rigs, checking one out for a session and releasing it
when done, with a FIFO queue when everything is busy. The rigs are
simulated; see README.
"""
from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class RigStatus(Enum):
    FREE = "FREE"
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"
    FAULTY = "FAULTY"


@dataclass
class Rig:
    rig_id: str
    status: RigStatus = RigStatus.FREE
    held_by: str | None = None
    consecutive_health_failures: int = 0


class RigCheckoutError(Exception):
    pass


class RigPool:
    """A pool of rigs with checkout/release and FIFO queueing.

    Checkout semantics:
      - If a FREE rig exists, it's reserved immediately for the caller.
      - If none are FREE, the caller is queued (FIFO) and must call
        try_dequeue() (or the pool's release() path) to get served once a
        rig frees up — this mirrors a real remote-access broker where a
        session request either succeeds immediately or waits its turn.
      - FAULTY/MAINTENANCE rigs are never handed out.
    """

    def __init__(self, rig_ids):
        self.rigs = {rid: Rig(rig_id=rid) for rid in rig_ids}
        self.queue = deque()

    def _first_free_rig(self):
        for rig in self.rigs.values():
            if rig.status == RigStatus.FREE:
                return rig
        return None

    def checkout(self, user):
        """Attempts to reserve a rig for `user`. Returns the rig_id if
        immediately available, or None if the user was queued instead."""
        rig = self._first_free_rig()
        if rig is not None:
            rig.status = RigStatus.RESERVED
            rig.held_by = user
            return rig.rig_id
        self.queue.append(user)
        return None

    def begin_use(self, rig_id, user):
        """Transitions a RESERVED rig to IN_USE once the session actually
        starts (separates 'reserved for you' from 'you're actively using
        it now', matching how a real remote-access tool would report
        state to a dashboard)."""
        rig = self.rigs[rig_id]
        if rig.status != RigStatus.RESERVED or rig.held_by != user:
            raise RigCheckoutError(f"Rig {rig_id} is not reserved for {user}")
        rig.status = RigStatus.IN_USE

    def release(self, rig_id, user):
        """Releases a rig back to the pool. If anyone is queued, the next
        person in line is immediately given the rig (still RESERVED, they
        must call begin_use themselves) rather than leaving it FREE and
        racy."""
        rig = self.rigs[rig_id]
        if rig.held_by != user:
            raise RigCheckoutError(f"Rig {rig_id} is not held by {user}")

        if self.queue:
            next_user = self.queue.popleft()
            rig.held_by = next_user
            rig.status = RigStatus.RESERVED
            return next_user  # caller can notify this user their turn came
        else:
            rig.status = RigStatus.FREE
            rig.held_by = None
            return None

    def mark_faulty(self, rig_id):
        """Pulls a rig out of service. A faulty rig is never handed out by
        checkout(), even if it was previously FREE."""
        rig = self.rigs[rig_id]
        rig.status = RigStatus.FAULTY
        rig.held_by = None

    def clear_fault(self, rig_id):
        """Manually resets a rig back into service after maintenance."""
        rig = self.rigs[rig_id]
        rig.status = RigStatus.FREE
        rig.held_by = None
        rig.consecutive_health_failures = 0

    def status_counts(self):
        counts = {status: 0 for status in RigStatus}
        for rig in self.rigs.values():
            counts[rig.status] += 1
        return counts

    def queue_depth(self):
        return len(self.queue)
