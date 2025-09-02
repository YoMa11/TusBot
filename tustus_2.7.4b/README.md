# tustus_2.7.4b

- Run `bash botctl.sh setup` then `bash botctl.sh start`.
- Uses `config.py` as provided (unchanged).
- Scrapes `config.URL` every `config.INTERVAL` seconds.
- Stores into `flights.db` table `show_item(destination, price, currency, url, last_seen)`.
