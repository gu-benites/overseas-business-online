# China Entry Nodes

To improve connectivity and reliability when accessing our Residential Proxies from China (or nearby regions), we provide a set of alternative regional entry domains.

These domains function exactly like our standard proxy gateway, but may offer better stability, lower latency, and fewer connection issues for specific geographies.

| Region    | Entry domain    |
| --------- | --------------- |
| US        | us.xpt9k2wq.com |
| Europe    | eu.xpt9k2wq.com |
| Singapore | sg.xpt9k2wq.com |
| Hong Kong | hk.xpt9k2wq.com |
| Australia | au.xpt9k2wq.com |

### How to Use These Nodes

Simply replace your usual proxy hostname with one of the regional domains.

Here's a cURL example with Singapore entry domain:

{% tabs %}
{% tab title="cURL" %}

```bash
curl -v -x http://username123:password321@sg.xpt9k2wq.com:12321 -L https://ipv4.icanhazip.com
```

{% endtab %}
{% endtabs %}

{% hint style="warning" %}
NOTE: Geo-routing is not supported using these nodes at the moment.
{% endhint %}
