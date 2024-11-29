# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: raft.proto
# Protobuf Python Version: 5.28.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    28,
    1,
    '',
    'raft.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\nraft.proto\x12\x04raft\"K\n\x08LogEntry\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x0f\n\x07\x63ommand\x18\x02 \x01(\x0c\x12\x11\n\ttimestamp\x18\x03 \x01(\x03\x12\r\n\x05index\x18\x04 \x01(\x03\"b\n\x12RequestVoteRequest\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x13\n\x0b\x63\x61ndidateId\x18\x02 \x01(\x05\x12\x14\n\x0clastLogIndex\x18\x03 \x01(\x03\x12\x13\n\x0blastLogTerm\x18\x04 \x01(\x03\"8\n\x13RequestVoteResponse\x12\x13\n\x0bvoteGranted\x18\x01 \x01(\x08\x12\x0c\n\x04term\x18\x02 \x01(\x05\"\x98\x01\n\x14\x41ppendEntriesRequest\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x10\n\x08leaderId\x18\x02 \x01(\x05\x12\x14\n\x0cprevLogIndex\x18\x03 \x01(\x03\x12\x13\n\x0bprevLogTerm\x18\x04 \x01(\x03\x12\x1f\n\x07\x65ntries\x18\x05 \x03(\x0b\x32\x0e.raft.LogEntry\x12\x14\n\x0cleaderCommit\x18\x06 \x01(\x03\"J\n\x15\x41ppendEntriesResponse\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x0f\n\x07success\x18\x02 \x01(\x08\x12\x12\n\nmatchIndex\x18\x03 \x01(\x03\"1\n\rClientRequest\x12\x0f\n\x07\x63ommand\x18\x01 \x01(\x0c\x12\x0f\n\x07\x64\x62_name\x18\x02 \x01(\t\"H\n\x0e\x43lientResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x10\n\x08response\x18\x02 \x01(\t\x12\x13\n\x0bleader_hint\x18\x03 \x01(\t\" \n\rStatusRequest\x12\x0f\n\x07node_id\x18\x01 \x01(\x05\"\x82\x01\n\x0eStatusResponse\x12\r\n\x05state\x18\x01 \x01(\t\x12\x14\n\x0c\x63urrent_term\x18\x02 \x01(\x05\x12\x16\n\x0elast_log_index\x18\x03 \x01(\x03\x12\x11\n\tlog_count\x18\x04 \x01(\x05\x12\x11\n\tis_leader\x18\x05 \x01(\x08\x12\r\n\x05peers\x18\x06 \x03(\t2\x8c\x02\n\x0bRaftService\x12\x33\n\x06Status\x12\x13.raft.StatusRequest\x1a\x14.raft.StatusResponse\x12\x42\n\x0bRequestVote\x12\x18.raft.RequestVoteRequest\x1a\x19.raft.RequestVoteResponse\x12H\n\rAppendEntries\x12\x1a.raft.AppendEntriesRequest\x1a\x1b.raft.AppendEntriesResponse\x12:\n\rClientCommand\x12\x13.raft.ClientRequest\x1a\x14.raft.ClientResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'raft_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_LOGENTRY']._serialized_start=20
  _globals['_LOGENTRY']._serialized_end=95
  _globals['_REQUESTVOTEREQUEST']._serialized_start=97
  _globals['_REQUESTVOTEREQUEST']._serialized_end=195
  _globals['_REQUESTVOTERESPONSE']._serialized_start=197
  _globals['_REQUESTVOTERESPONSE']._serialized_end=253
  _globals['_APPENDENTRIESREQUEST']._serialized_start=256
  _globals['_APPENDENTRIESREQUEST']._serialized_end=408
  _globals['_APPENDENTRIESRESPONSE']._serialized_start=410
  _globals['_APPENDENTRIESRESPONSE']._serialized_end=484
  _globals['_CLIENTREQUEST']._serialized_start=486
  _globals['_CLIENTREQUEST']._serialized_end=535
  _globals['_CLIENTRESPONSE']._serialized_start=537
  _globals['_CLIENTRESPONSE']._serialized_end=609
  _globals['_STATUSREQUEST']._serialized_start=611
  _globals['_STATUSREQUEST']._serialized_end=643
  _globals['_STATUSRESPONSE']._serialized_start=646
  _globals['_STATUSRESPONSE']._serialized_end=776
  _globals['_RAFTSERVICE']._serialized_start=779
  _globals['_RAFTSERVICE']._serialized_end=1047
# @@protoc_insertion_point(module_scope)
