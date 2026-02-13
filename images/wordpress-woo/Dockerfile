FROM wordpress:6.6.2-php8.3-apache

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Bundle WooCommerce plugin into the image for deterministic provisioning.
RUN mkdir -p /tmp/woo \
    && curl -fsSL https://downloads.wordpress.org/plugin/woocommerce.latest-stable.zip -o /tmp/woo/woocommerce.zip \
    && unzip /tmp/woo/woocommerce.zip -d /usr/src/wordpress/wp-content/plugins \
    && rm -rf /tmp/woo
