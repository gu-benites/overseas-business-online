# Geo-location Targeting

You can specify a country, city or a US state, from which to access your target website.

### Country Targeting

You can enable country-level targeting by appending `_country-` to the password in your proxy credentials.

Example usage for US:

```
curl -k -v -x http://unblocker.iproyal.com:12323 --proxy-user user:password_country-us -L https://ipv4.icanhazip.com
```

The value of this parameter is a two-letter country code ([ISO 3166-1 alpha-2 format](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)).

You can set more than one country at once.

### City Targeting

For city-level targeting, append the `_city-` key to the password in your proxy credentials. Its value should be the name of the city.

{% hint style="info" %}
NOTE: It's essential to first specify the country using `_country-` key when targeting a specific city, as multiple countries may have cities with the same name.
{% endhint %}

Example:

```
curl -k -v -x http://unblocker.iproyal.com:12323 --proxy-user user:password_country-us_city-chicago -L https://ipv4.icanhazip.com
```

### State Targeting

This feature allows state-level **targeting only in US**. To target a specific state, append the `_state-` key to the password in your proxy credentials. Its value should be the name of the state.

Example:

```
curl -k -v -x http://unblocker.iproyal.com:12323 --proxy-user user:password_country-us_state-iowa -L https://ipv4.icanhazip.com
```

\ <br>
