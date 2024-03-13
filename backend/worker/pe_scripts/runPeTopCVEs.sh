#!/bin/bash

cd /app/pe-reports || return

pe-source cybersixgill --cybersix-methods=topCVEs --soc_med_included
