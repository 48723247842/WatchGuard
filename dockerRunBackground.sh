#!/bin/bash

sudo docker rm -f "watch-guard"

sudo docker run -dit --restart='always' \
--name 'watch-guard' \
-p 11001:11001
watch-guard