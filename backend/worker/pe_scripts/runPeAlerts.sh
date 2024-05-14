#!/bin/bash

cd /app/pe-reports || return

pe-source cybersixgill --cybersix-methods=alerts --soc_med_included
