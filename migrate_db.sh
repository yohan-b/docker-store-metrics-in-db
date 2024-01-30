#!/bin/bash

flask db init; flask db migrate -m "Database migration." && flask db upgrade
