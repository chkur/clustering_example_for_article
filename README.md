## Running project

Build docker containers
```
docker-compose up --build -d
```

Import data. This command will download sample file from Chicago City Portal and import its data to the database.

You can download this file manually from https://data.cityofchicago.org/api/views/3c9v-pnva/rows.csv?accessType=DOWNLOAD and place it to the folder `files` inside project with name `example.csv`.

```
docker-compose exec web python manage.py import_rows
```
## Example map queries with clustering

### Slower

http://localhost:8000/api/vehicles/map/?max_lat=42&max_lon=-87.6&min_lat=41.8491660012213&min_lon=-87.70814559957574 - 28.24c

### Faster

http://localhost:8000/api/vehicles/map_fast/?max_lat=42&max_lon=-87.6&min_lat=41.8491660012213&min_lon=-87.70814559957574 - 2.25c
