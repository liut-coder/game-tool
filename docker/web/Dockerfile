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
RUN yum -y install https://archives.fedoraproject.org/pub/archive/epel/7/x86_64/Packages/e/epel-release-7-14.noarch.rpm \
    && printf '%s\n' \
        '[epel]' \
        'name=Extra Packages for Enterprise Linux 7 - $basearch' \
        'baseurl=http://archives.fedoraproject.org/pub/archive/epel/7/$basearch' \
        'enabled=1' \
        'gpgcheck=0' > /etc/yum.repos.d/epel.repo \
    && yum -y update \
    && yum -y install nginx php php-fpm php-cli php-mysql php-mbstring php-gd php-curl php-xml php-common procps-ng net-tools \
    && yum clean all

COPY nginx.conf /etc/nginx/nginx.conf
COPY web-entrypoint.sh /usr/local/bin/web-entrypoint.sh
RUN chmod +x /usr/local/bin/web-entrypoint.sh \
    && sed -i 's/^;*short_open_tag = .*/short_open_tag = On/' /etc/php.ini \
    && sed -i 's/^;*date.timezone =.*/date.timezone = Asia\/Shanghai/' /etc/php.ini \
    && sed -i 's/^user = .*/user = nginx/' /etc/php-fpm.d/www.conf \
    && sed -i 's/^group = .*/group = nginx/' /etc/php-fpm.d/www.conf \
    && sed -i 's#^listen = .*#listen = 127.0.0.1:9000#' /etc/php-fpm.d/www.conf \
    && sed -i 's/^;*listen.allowed_clients = .*/listen.allowed_clients = 127.0.0.1/' /etc/php-fpm.d/www.conf

CMD ["/usr/local/bin/web-entrypoint.sh"]
