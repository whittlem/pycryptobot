# Run bot(s) as Linux systemd service(s)

Configure pycryptobot to run as a Linux **systemd service**. Services can be launched automatically every time
the server boots.  
The services are managed using the systemd controls: _start, stop, status, restart, enable, disable_  

## Creating a Python virtual Environment
It is a best Python practice running applications in separate virtual environments.
This avoids that the Python working environment is altered when the operating system is updated. 
An additional library that support Python virtual environments, is required:  

    sudo apt install -y python3-venv  

Once installed, a virtual environment can be created and activated. Note that a single virtual environment is shared 
by all pycryptobots:  

    python3 -m venv ~/.venvs
    source ~/.venvs/bin/activate

Also append the environment activation line to `.bashrc` This activates the virtual environment every time a shell 
opens (i.e. via ssh):

    echo 'source ~/.venvs/bin/activate' >> ~/.bashrc

## Creating a systemd service file
To run a pycryptobot as a `systemd` service, create for each bot a systemd service file in the systemd services
configuration folder `/etc/systemd/system`  

For each currency create a new service file: 

    sudo nano /etc/systemd/system/<service-name>.service

Choosing a service name that contains the names of the crypto and fiat currencies simplifies later services management.
_Example:_  `sudo nano /etc/systemd/system/ada-eur.service`

Paste the lines below into each service file:

    [Unit]  
    Description=PyCryptobot - <currency name>  
    After=network.target  
      
    [Service]  
    User=ubuntu  
    Group=ubuntu  
    WorkingDirectory=/home/ubuntu/<folder where the pycryptobot code and config resides>  
    Environment="PATH=/home/ubuntu/.venvs/bin/python3"  
    ExecStart=/home/ubuntu/.venvs/bin/python3 pycryptobot.py  
    Restart=on-failure

    [Install]  
    WantedBy=multi-user.target  

Replace the `<placeholders>` in the lines `Description=` and `WorkingDirectory=` with correct data for the currency \
being configured.

Let systemd reload the service files and update the list of available services with the newly added files:   

    sudo systemctl daemon-reload

_NOTE:_ this step has to be repeated every time a service file is updated

Now the service(s) are available and can be managed using the standard systemd controls:

#### To START a pycryptobot service
A single service:

    sudo systemctl start ada-eur.service

Multiple services:

    sudo systemctl start ada-eur.service bch-eur.service btc-eur.service eos-eur.service eth-eur.service ltc-eur.service

or even with a wildcard: 

    sudo systemctl start *-eur.service

#### To STOP a pycryptobot service
A single service:

    sudo systemctl stop ada-eur.service

Multiple services:

    sudo systemctl stop ada-eur.service bch-eur.service btc-eur.service eos-eur.service eth-eur.service ltc-eur.service

or even with a wildcard: 

    sudo systemctl stop *-eur.service

#### ENABLE or DISABLE services to launch during server startup
Enabling the service(s) to start at startup once a network connection is available: 

    sudo systemctl enable *-eur.service 

which enables all services in one go.

Disabling the service(s) to start at startup: 

    sudo systemctl disable *-eur.service 

which disables all services in one go.

#### Query the STATUS of a(ll) service(s)

To query the status of a service or all services: 

    sudo systemctl status *-eur.service
