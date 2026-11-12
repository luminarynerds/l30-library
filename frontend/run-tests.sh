#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
cd /opt/l30/frontend
export NODE_ENV=test
/opt/l30/frontend/node_modules/.bin/vitest run --reporter=verbose
