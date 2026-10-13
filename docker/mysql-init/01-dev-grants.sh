#!/bin/sh
set -e

# DEV ONLY: lets the app user create the temporary test database that pytest needs.
mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
GRANT ALL PRIVILEGES ON *.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
SQL
