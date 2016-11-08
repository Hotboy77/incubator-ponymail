#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os
import getpass
import subprocess
import argparse
import shutil

if sys.version_info <= (3, 3):
    print("This script requires Python 3.4 or higher")
    sys.exit(-1)

dopip = False
try:
    from elasticsearch import Elasticsearch
except:
    dopip = True
    
if dopip and (getpass.getuser() != "root"):
    print("It looks like you need to install some python modules first")
    print("Either run this as root to do so, or run: ")
    print("pip3 install elasticsearch formatflowed netaddr")
    sys.exit(-1)

elif dopip:
    print("Before we get started, we need to install some modules")
    print("Hang on!")
    try:
        subprocess.check_call(('pip3','install','elasticsearch','formatflowed', 'netaddr'))
        from elasticsearch import Elasticsearch
    except:
        print("Oh dear, looks like this failed :(")
        print("Please install elasticsearch and formatflowed before you try again:")
        print("pip install elasticsearch formatflowed netaddr")
        sys.exit(-1)


# CLI arg parsing
parser = argparse.ArgumentParser(description='Command line options.')

parser.add_argument('--defaults', dest='defaults', action='store_true', 
                   help='Use default settings')

parser.add_argument('--dbhost', dest='dbhost', type=str, nargs=1,
                   help='ES backend hostname')
parser.add_argument('--dbport', dest='dbport', type=str, nargs=1,
                   help='DB port')
parser.add_argument('--dbname', dest='dbname', type=str, nargs=1,
                   help='ES DB name')
parser.add_argument('--mailserver', dest='mailserver', type=str, nargs=1,
                   help='Host name of outgoing mail server')
parser.add_argument('--mldom', dest='mldom', type=str, nargs=1,
                   help='Domains to accept mail for via UI')
parser.add_argument('--wordcloud', dest='wc', action='store_true', 
                   help='Enable word cloud')
parser.add_argument('--skiponexist', dest='soe', action='store_true', 
                   help='Skip setup if ES index exists')
parser.add_argument('--noindex', dest='noi', action='store_true', 
                   help="Don't make an ES index, assume it exists")
parser.add_argument('--nocloud', dest='nwc', action='store_true', 
                   help='Do not enable word cloud')
args = parser.parse_args()    

print("Welcome to the Pony Mail setup script!")
print("Let's start by determining some settings...")
print("")


hostname = ""
port = 0
dbname = ""
mlserver = ""
mldom = ""
wc = ""
wce = False



# If called with --defaults (like from Docker), use default values
if args.defaults:
    hostname = "localhost"
    port = 9200
    dbname = "ponymail"
    mlserver = "localhost"
    mldom = "example.org"
    wc = "Y"
    wce = True

# Accept CLI args, copy them
if args.dbhost:
    hostname = args.dbhost[0]
if args.dbport:
    port = int(args.dbport[0])
if args.dbname:
    dbname = args.dbname[0]
if args.mailserver:
    mlserver = args.mailserver[0]
if args.mldom:
    mldom = args.mldom[0]
if args.wc:
    wc = args.wc
if args.nwc:
    wc = False
    
while hostname == "":
    hostname = input("What is the hostname of the ElasticSearch server? (e.g. localhost): ")
    
while port < 1:
    try:
        port = int(input("What port is ElasticSearch listening on? (normally 9200): "))
    except ValueError:
        pass

while dbname == "":
    dbname = input("What would you like to call the mail index (e.g. ponymail): ")

while mlserver == "":
    mlserver = input("What is the hostname of the outgoing mailserver? (e.g. mail.foo.org): ")
    
while mldom == "":
    mldom = input("Which domains would you accept mail to from web-replies? (e.g. foo.org or *): ")

while wc == "":
    wc = input("Would you like to enable the word cloud feature? (Y/N): ")
    if wc.lower() == "y":
        wce = True


print("Okay, I got all I need, setting up Pony Mail...")

def createIndex():
    es = Elasticsearch([
        {
            'host': hostname,
            'port': port,
            'use_ssl': False,
            'url_prefix': ''
        }],
        max_retries=5,
        retry_on_timeout=True
        )

    # Check if index already exists
    if es.indices.exists(dbname):
        if args.soe:
            print("ElasticSearch index '%s' already exists and SOE set, exiting quietly" % dbname)
            sys.exit(0)
        else:
            print("Error: ElasticSearch index '%s' already exists!" % dbname)
            sys.exit(-1)

    print("Creating index " + dbname)

    mappings = {
        "mbox" : {
          "properties" : {
            "@import_timestamp" : {
              "type" : "date",
              "format" : "yyyy/MM/dd HH:mm:ss||yyyy/MM/dd"
            },
            "attachments" : {
              "properties" : {
                "content_type" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                },
                "filename" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                },
                "hash" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                },
                "size" : {
                  "type" : "long"
                }
              }
            },
            "body" : {
              "type" : "string"
            },
            "cc": {
              "type": "string"
            },
            "date" : {
              "type" : "date",
              "store" : True,
              "format" : "yyyy/MM/dd HH:mm:ss",
              "index" : "not_analyzed"
            },
            "epoch" : { # number of seconds since the epoch
              "type" : "double",
              "index" : "not_analyzed"
            },
            "from" : {
              "type" : "string"
            },
            "from_raw" : {
              "type" : "string",
              "index" : "not_analyzed"
            },
            "in-reply-to" : {
              "type" : "string"
            },
            "list" : {
              "type" : "string"
            },
            "list_raw" : {
              "type" : "string",
              "index" : "not_analyzed"
            },
            "message-id" : {
              "type" : "string",
              "index" : "not_analyzed"
            },
            "mid" : {
              "type" : "string"
            },
            "private" : {
              "type" : "boolean"
            },
            "references" : {
              "type" : "string"
            },
            "subject" : {
              "type" : "string"
            },
            "to" : {
              "type" : "string"
            }
          }
        },
        "attachment" : {
          "properties" : {
            "source" : {
              "type" : "binary"
            }
          }
        },
        "mbox_source" : {
          "_all": {
            "enabled": false # this doc type is not searchable
          },
          "properties" : {
            "source" : {
              "type" : "binary"
            },
            "message-id" : {
              "type" : "string",
              "index" : "not_analyzed"
            },
            "mid" : {
              "type" : "string"
            }
          }
        },
        "mailinglists" : {
          "_all": {
            "enabled": false # this doc type is not searchable
          },
          "properties" : {
            "description" : {
              "type" : "string",
              "index" : "not_analyzed"
            },
            "list" : {
              "type" : "string",
#               "index" : "not_analyzed"
            },
            "name" : {
              "type" : "string",
              "index" : "not_analyzed"
            }
          }
        },
        "account" : {
          "_all": {
            "enabled": false # this doc type is not searchable
          },
          "properties" : {
            "cid" : {
              "type" : "string",
              "index" : "not_analyzed"
            },
            "credentials" : {
              "properties" : {
                "altemail" : {
                  "type" : "object"
                },
                "email" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                },
                "fullname" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                },
                "uid" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                }
              }
            },
            "internal" : {
              "properties" : {
                "cookie" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                },
                "ip" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                },
                "oauth_used" : {
                  "type" : "string",
                  "index" : "not_analyzed"
                }
              }
            },
            "request_id" : {
              "type" : "string",
              "index" : "not_analyzed"
            }
          }
        },
        "notifications" : {
          "_all": {
            "enabled": false # this doc type is not searchable
          },
          "properties" : {
            "date" : {
              "type" : "date",
              "store" : True,
              "format" : "yyyy/MM/dd HH:mm:ss"
            },
            "epoch" : {
              "type" : "double"
            },
            "from" : {
              "type" : "string",
#               "index" : "not_analyzed"
            },
            "in-reply-to" : {
              "type" : "string",
#               "index" : "not_analyzed"
            },
            "list" : {
              "type" : "string",
#               "index" : "not_analyzed"
            },
            "message-id" : {
              "type" : "string",
              "index" : "not_analyzed"
            },
            "mid" : {
              "type" : "string",
#               "index" : "not_analyzed"
            },
            "private" : {
              "type" : "boolean"
            },
            "recipient" : {
              "type" : "string",
              "index" : "not_analyzed"
            },
            "seen" : {
              "type" : "long"
            },
            "subject" : {
              "type" : "string",
#               "index" : "not_analyzed"
            },
            "to" : {
              "type" : "string",
#               "index" : "not_analyzed"
            },
            "type" : {
              "type" : "string",
              "index" : "not_analyzed"
            }
          }
        }
    }
 
    res = es.indices.create(index = dbname, body = {
                "mappings" : mappings
            }
        )
    
    print("Index created!")
    
if not args.noi:
    try:
        createIndex()
    except Exception as e:
        print("Index creation failed: %s" % e)
        sys.exit(1)

print("Writing importer config (ponymail.cfg)")

with open("ponymail.cfg", "w") as f:
    f.write("""
###############################################################
# Pony Mail Configuration file                                             

# Main ES configuration
[elasticsearch]
hostname:               %s
dbname:                 %s
port:                   %u
ssl:                    false

#uri:                   url_prefix

#user:                  username
#password:              password

#write:                 consistency level (default quorum)

#backup:                database name

[archiver]
#generator:             medium|full|other

[debug]
#cropout:               string to crop from list-id

###############################################################
            """ % (hostname, dbname, port))
    f.close()
    
print("mod_lua configuration (config.lua)")
with open("../site/api/lib/config.lua", "w") as f:
    f.write("""
local config = {
    es_url = "http://%s:%u/%s/",
    mailserver = "%s",
    accepted_domains = "%s",
    wordcloud = %s,
    slow_count = false,
    email_footer = nil, -- see the docs for how to set this up.
    full_headers = false,
    maxResults = 5000, -- max emails to return in one go. Might need to be bumped for large lists
    admin_oauth = {}, -- list of domains that may do administrative oauth (private list access)
                     -- add 'www.googleapis.com' to the list for google oauth to decide, for instance.
    oauth_fields = { -- used for specifying individual oauth handling parameters.
-- for example:
--        internal = {
--            email = 'CAS-EMAIL',
--            name = 'CAS-NAME',
--            uid = 'REMOTE-USER',
--            env = 'subprocess' -- use environment vars instead of request headers
--        }
    },
    antispam = true  -- Whether or not to add anti-spam measures aimed at anonymous users.
    -- no_association = {} -- domains that are not allowed for email association
    -- hidePrivate = true -- whether to hide names of lists that contain any private mails
    -- listsDisplay = 'regex' -- if defined, hide list names that don't match the regex
}
return config
            """ % (hostname, port, dbname, mlserver, mldom, "true" if wce else "false"))
    f.close()
    
print("Copying sample JS config to config.js (if needed)...")
if not os.path.exists("../site/js/config.js") and os.path.exists("../site/js/config.js.sample"):
    shutil.copy("../site/js/config.js.sample", "../site/js/config.js")
    
    
print("All done, Pony Mail should...work now :)")
print("If you are using an external mail inbound server, \nmake sure to copy archiver.py and ponymail.cfg to it")
