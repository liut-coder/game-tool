FROM centos:7

RUN printf '%s\n' \
    '[base]' \
    'name=CentOS-7.9.2009 - Base' \
    'baseurl=http://vault.centos.org/7.9.2009/os/$basearch/' \
    'gpgcheck=0' \
    'enabled=1' \
    '[updates]' \
    'name=CentOS-7.9.2009 - Updates' \
    'baseurl=http://vault.centos.org/7.9.2009/updates/$basearch/' \
    'gpgcheck=0' \
    'enabled=1' \
    '[extras]' \
    'name=CentOS-7.9.2009 - Extras' \
    'baseurl=http://vault.centos.org/7.9.2009/extras/$basearch/' \
    'gpgcheck=0' \
    'enabled=1' > /etc/yum.repos.d/CentOS-Base.repo
RUN yum -y update \
    && yum -y install glibc.i686 libstdc++.i686 libgcc.i686 zlib.i686 ncurses-libs.i686 mariadb-libs.i686 file procps-ng net-tools psmisc which \
    && yum clean all

COPY start-game.sh /usr/local/bin/start-game.sh
RUN chmod +x /usr/local/bin/start-game.sh
CMD ["/usr/local/bin/start-game.sh"]
