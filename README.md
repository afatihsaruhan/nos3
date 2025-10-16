# Linux Ubuntu Kurulumu 22.04 ve üzeri versiyonlar olmalı, ardından terminali açarak alttaki gereksinimleri yükleyelim
---
# Docker Kurulumu, Network ve Grup Ayarları

```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt-get remove $pkg
done
```
``` # Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```
```sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin```

```sudo systemctl status docker``` => **YEŞİL (ACTİVATE) yazısını gördükten sonra CTRL+C yapıp devam edin**

```
sudo groupadd docker
sudo usermod -aG docker $USER
sudo reboot now
```
---

# Git Kurulumu

``` sudo apt-get install git```

# Repoyu Locale Çekme ve Gereksinimleri Yükleme

``` git clone https://github.com/nasa/nos3 ```

``` cd nos3```

``` git submodule update --init --recursive```

# Python Ortamının Kurulumu

```sudo apt install python3-pip python3-venv python3-dev```

# Python .venv dosyası oluşturma ve aktif etme (NOT, Sistem ya da terminal her açıldığında ~./nos3 dizininde ' source .venv/bin/activate ' komutunu terminale girmeden programı başlatamazsınız!!

```python3 -m venv .venv```

```source .venv/bin/activate```

# Data Toplama, Log Dosyaları Oluşturma ve Log Dosyalarını Data Merkezine Pushlama Script Ortamı Kurulumu

=> BURASI HENÜZ PROSEDÜR ALTINA ALINMADI.

# NASA Operational Simulator for Small Satellites (NOS3)

NOS3 is a suite of tools developed by NASA's Katherine Johnson Independent Verification and Validation (IV&V) Facility to aid in areas such as software development, integration & test (I&T), mission operations/training, verification and validation (V&V), and software systems check-out. 
NOS3 provides a software development environment, a multi-target build system, an operator interface/ground station, dynamics and environment simulations, and software-based models of spacecraft hardware.

# Documentation

[NOS3 - ReadTheDocs](https://nos3.readthedocs.io/en/latest/)

## Issues and Feature Requests

Please report issues and request features on the GitHub tracking system - [NOS3 Issues](https://www.github.com/nasa/nos3/issues).

If you would like to contribute to the repository, please complete this [NASA Form][def] and submit it to gsfc-softwarerequest@mail.nasa.gov with Justin.R.Morris@nasa.gov CC'ed.
Next, please create an issue describing the work to be performed noting that you intend to work it, create a related branch, and submit a pull request when ready. When complete, we will review and work to get it integrated.

If this project interests you or if you have any questions, please feel free to open an issue or discussion on the GitHub, contact any developer directly, or email `support@nos3.org`.

[def]: https://github.com/nasa/nos3/files/14578604/NOS3_Invd_CLA.pdf "NOS3 NASA Contributor Form PDF"

## License

This project is licensed under the NOSA 1.3 (NASA Open Source Agreement) License. 

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the tags on this repository.
