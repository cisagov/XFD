#!/bin/bash

cd /app/pe-reports || return

pe-source shodan --soc_med_included
