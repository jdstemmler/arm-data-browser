# ENA Data Browser

## ABOUT

The ENA Data Browser is a tool put together and maintained by Jayson Stemmler of the University of Washington as a way to more easily look at and investigate the data from the permanent field site on Graciosa Island.

Go check out the site at [ena.jdstemmler.com](http://ena.jdstemmler.com)

## SETUP

Just about everything you need to get the basic site up and running should be included. The installation has been tested to work (and is currently running) on an AWS instance running Ubuntu 14.04.4 LTS with Nginx.

I will not cover setting up python right now. I will do that in the future, but I mostly just need to write down where some of these files go.

https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-16-04

### Files
* `cp nginx.conf /etc/nginx/sites-available/ena_application`
* `cp ena_application.conf /etc/init/ena_application.conf`

The `nginx.conf` file tells the Nginx server how to direct the request to the root URL.

The `ena_application.conf` file starts up the uWSGI deployment so that the app runs.

I leave it as an exercise for the reader to go through and see which values need to get changed - you'll likely need to change the paths to the application to suit your needs. Other files that you may need to modify include

* `ena_application.ini`
* `wsgi.py`
