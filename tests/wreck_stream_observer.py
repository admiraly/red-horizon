"""Development peer retains wreck snapshots consumed while waiting for command ACKs."""
from collections import deque
from test_coop import Peer
class RecordingPeer(Peer):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.wreck_queue=deque();self.recording_request=False
 def request(self,*args,**kwargs):
  self.recording_request=True
  try:return super().request(*args,**kwargs)
  finally:self.recording_request=False
 def receive(self,timeout=.1):
  if self.wreck_queue and not self.recording_request:return self.wreck_queue.popleft()
  row=super().receive(timeout)
  if self.recording_request and row and row[0][4]==106:self.wreck_queue.append(row)
  return row
