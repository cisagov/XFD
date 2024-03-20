#!/bin/bash

cd /app/pe-reports || return

pe-source cybersixgill --cybersix-methods=credentials --soc_med_included
