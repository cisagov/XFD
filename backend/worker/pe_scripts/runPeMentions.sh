#!/bin/bash

cd /app/pe-reports || return

pe-source cybersixgill --cybersix-methods=mentions --soc_med_included
