# Access

## Get Entry Nodes

<mark style="color:green;">`GET`</mark>  `/access/entry-nodes`

Different entry nodes help to determine the faster route from the country you are situated in.

{% hint style="info" %}
In almost all cases, you should use **`geo.iproyal.com`** which will automatically determine the best server for your location.
{% endhint %}

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET https://resi-api.iproyal.com/v1/access/entry-nodes \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/access/entry-nodes';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPGET, true);
$headers = [
    "Authorization: Bearer $api_token"
];
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);

if (curl_errno($ch)) {
    echo 'Error:' . curl_error($ch);
} else {
    echo $response;
}

curl_close($ch);
?>
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

api_token = '<your_api_token>'
url = 'https://resi-api.iproyal.com/v1/access/entry-nodes'

headers = {
    'Authorization': f'Bearer {api_token}'
}

response = requests.get(url, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';
const url = 'https://resi-api.iproyal.com/v1/access/entry-nodes';

const options = {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${apiToken}`
  }
};

const req = https.request(url, options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log(data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.end();
```

{% endtab %}

{% tab title="Java" %}

```java
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiRequest {
    public static void main(String[] args) {
        String apiToken = "<your_api_token>";
        String urlString = "https://resi-api.iproyal.com/v1/access/entry-nodes";

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);

            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                String inputLine;
                StringBuilder content = new StringBuilder();

                while ((inputLine = in.readLine()) != null) {
                    content.append(inputLine);
                }
                in.close();

                System.out.println(content.toString());
            } else {
                System.out.println("GET request failed. Response Code: " + responseCode);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
	"io"
	"log"
	"net/http"
	"fmt"
)

const (
	apiToken     = "<your_api_token>"
	entryNodesURL = "https://resi-api.iproyal.com/v1/access/entry-nodes"
)

func main() {
	req, err := http.NewRequest(http.MethodGet, entryNodesURL, nil)
	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiToken)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatal("Error making request:", err)
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal("Error reading response body:", err)
	}

	fmt.Println(string(responseBody))
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System;
using System.Net.Http;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/access/entry-nodes";

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            HttpResponseMessage response = await client.GetAsync(url);

            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}

**Example response:**

```json
[
    {
        "dns": "proxy.iproyal.com",
        "ips": ["91.239.130.34"],
        "ports": [
            {
                "name": "http|https",
                "port": 12321,
                "alternative_ports": [
                    11200,
                    ...
                ]
            },
            {
                "name": "socks5",
                "port": 32325,
                "alternative_ports": [
                    51200,
                    ...
                ]
            }
        ]
    },
    {
        "dns": "us.proxy.iproyal.com",
        "ips": ["23.146.144.102", "23.146.144.102"],
        "ports": [
            {
                "name": "http|https",
                "port": 12321,
                "alternative_ports": [
                    11246,
                    ...
                ]
            },
            {
                "name": "socks5",
                "port": 32325,
                "alternative_ports": [
                    51200,
                    ...
                ]
            }
        ]
    },
    ...
]
```

## Get Countries

<mark style="color:green;">`GET`</mark>  `/access/countries`

Returns a list of countries, cities, states, and ISPs (Internet Service Providers) that could be used to target a specific proxy. It also returns prefixes to use for each. For more information on how to build a proxy string, refer to our 'Proxy' subsection.

[proxy](https://docs.iproyal.com/proxies/residential/proxy "mention")

{% hint style="info" %}
Depending on some settings set for you as a user, it will return different results.

* **Identity verification** - provides a larger selection of options.
* **Skip ISP Static** *(Admin activatable)* - on top of verified identity, skips static proxies.
* **ISPs enabled** (*Admin activatable*) - includes ISPs in every location.
  {% endhint %}

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET https://resi-api.iproyal.com/v1/access/countries \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/access/countries';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPGET, true);
$headers = [
    "Authorization: Bearer $api_token"
];
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);

if (curl_errno($ch)) {
    echo 'Error:' . curl_error($ch);
} else {
    echo $response;
}

curl_close($ch);
?>
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

api_token = '<your_api_token>'
url = 'https://resi-api.iproyal.com/v1/access/countries'

headers = {
    'Authorization': f'Bearer {api_token}'
}

response = requests.get(url, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';
const url = 'https://resi-api.iproyal.com/v1/access/countries';

const options = {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${apiToken}`
  }
};

const req = https.request(url, options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log(data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.end();
```

{% endtab %}

{% tab title="Java" %}

```java
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiRequest {
    public static void main(String[] args) {
        String apiToken = "<your_api_token>";
        String urlString = "https://resi-api.iproyal.com/v1/access/countries";

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);

            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                String inputLine;
                StringBuilder content = new StringBuilder();

                while ((inputLine = in.readLine()) != null) {
                    content.append(inputLine);
                }
                in.close();

                System.out.println(content.toString());
            } else {
                System.out.println("GET request failed. Response Code: " + responseCode);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
	"io"
	"log"
	"net/http"
	"fmt"
)

const (
	apiToken    = "<your_api_token>"
	countriesURL = "https://resi-api.iproyal.com/v1/access/countries"
)

func main() {
	req, err := http.NewRequest(http.MethodGet, countriesURL, nil)
	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiToken)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatal("Error making request:", err)
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal("Error reading response body:", err)
	}

	fmt.Println(string(responseBody))
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System;
using System.Net.Http;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/access/countries";

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            HttpResponseMessage response = await client.GetAsync(url);

            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}

**Example response:**

```json
{
    "prefix": "_country-",
    "countries": [
        {
            "code": "am",
            "name": "Armenia",
            "cities": {
                "prefix": "_city-",
                "options": [
                    {
                        "code": "armavir",
                        "name": "Armavir",
                        "isps": {
                            "prefix": "_isp-",
                            "options": [
                                {
                                    "code": "prostieresheniallc",
                                    "name": "Prostie Reshenia LLC"
                                }
                            ]
                        }
                    }
                ]
            },
            "states": {
                "prefix": "_state-",
                "options": [
                    {
                        "code": "armavir",
                        "name": "Armavir",
                        "cities": {
                            "prefix": "_city-",
                            "options": [
                                {
                                    "code": "armavir",
                                    "name": "Armavir",
                                    "isps": {
                                        "prefix": "_isp-",
                                        "options": []
                                    }
                                }
                            ]
                        },
                        "isps": {
                            "prefix": "_isp-",
                            "options": [
                                {
                                    "code": "prostieresheniallc",
                                    "name": "Prostie Reshenia LLC"
                                }
                            ]
                        }
                    }
                ]
            }
        }
    ]
}

```

## Get Regions

Similarly to [#countries](#countries "mention"), it returns available regions for use when targeting a proxy.

<mark style="color:green;">`GET`</mark>  `/access/regions`

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET https://resi-api.iproyal.com/v1/access/regions \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/access/regions';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPGET, true);
$headers = [
    "Authorization: Bearer $api_token"
];
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);

if (curl_errno($ch)) {
    echo 'Error:' . curl_error($ch);
} else {
    echo $response;
}

curl_close($ch);
?>
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

api_token = '<your_api_token>'
url = 'https://resi-api.iproyal.com/v1/access/regions'

headers = {
    'Authorization': f'Bearer {api_token}'
}

response = requests.get(url, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';
const url = 'https://resi-api.iproyal.com/v1/access/regions';

const options = {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${apiToken}`
  }
};

const req = https.request(url, options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log(data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.end();
```

{% endtab %}

{% tab title="Java" %}

```java
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiRequest {
    public static void main(String[] args) {
        String apiToken = "<your_api_token>";
        String urlString = "https://resi-api.iproyal.com/v1/access/regions";

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);

            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                String inputLine;
                StringBuilder content = new StringBuilder();

                while ((inputLine = in.readLine()) != null) {
                    content.append(inputLine);
                }
                in.close();

                System.out.println(content.toString());
            } else {
                System.out.println("GET request failed. Response Code: " + responseCode);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
	"io"
	"log"
	"net/http"
	"fmt"
)

const (
	apiToken  = "<your_api_token>"
	regionsURL = "https://resi-api.iproyal.com/v1/access/regions"
)

func main() {
	req, err := http.NewRequest(http.MethodGet, regionsURL, nil)
	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiToken)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatal("Error making request:", err)
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal("Error reading response body:", err)
	}

	fmt.Println(string(responseBody))
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System;
using System.Net.Http;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/access/regions";

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            HttpResponseMessage response = await client.GetAsync(url);

            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}

**Example response:**

```json
{
    "prefix": "_region-",
    "regions": [
        {
            "code": "africa",
            "name": "Africa"
        },
        {
            "code": "arabstates",
            "name": "Arab States"
        },
        {
            "code": "asiapacific",
            "name": "Asia & Pacific"
        },
        {
            "code": "europe",
            "name": "Europe"
        },
        {
            "code": "middleeast",
            "name": "Middle east"
        },
        {
            "code": "northamerica",
            "name": "North America"
        },
        {
            "code": "southlatinamerica",
            "name": "South/Latin America"
        }
    ]
}
```

## Get Country Sets

<mark style="color:green;">`GET`</mark>  `/access/country-sets`

Similarly to [#countries](#countries "mention"), it returns available country sets to use when targeting a proxy.

**Example request:**&#x20;

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET https://resi-api.iproyal.com/v1/access/country-sets \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/access/country-sets';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPGET, true);
$headers = [
    "Authorization: Bearer $api_token"
];
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);

if (curl_errno($ch)) {
    echo 'Error:' . curl_error($ch);
} else {
    echo $response;
}

curl_close($ch);
?>
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

api_token = '<your_api_token>'
url = 'https://resi-api.iproyal.com/v1/access/country-sets'

headers = {
    'Authorization': f'Bearer {api_token}'
}

response = requests.get(url, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';
const url = 'https://resi-api.iproyal.com/v1/access/country-sets';

const options = {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${apiToken}`
  }
};

const req = https.request(url, options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log(data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.end();
```

{% endtab %}

{% tab title="Java" %}

```java
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiRequest {
    public static void main(String[] args) {
        String apiToken = "<your_api_token>";
        String urlString = "https://resi-api.iproyal.com/v1/access/country-sets";

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);

            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                String inputLine;
                StringBuilder content = new StringBuilder();

                while ((inputLine = in.readLine()) != null) {
                    content.append(inputLine);
                }
                in.close();

                System.out.println(content.toString());
            } else {
                System.out.println("GET request failed. Response Code: " + responseCode);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
	"io"
	"log"
	"net/http"
	"fmt"
)

const (
	apiToken = "<your_api_token>"
	countrySetsURL = "https://resi-api.iproyal.com/v1/access/country-sets"
)

func main() {
	req, err := http.NewRequest(http.MethodGet, countrySetsURL, nil)
	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiToken)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatal("Error making request:", err)
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal("Error reading response body:", err)
	}

	fmt.Println(string(responseBody))
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System;
using System.Net.Http;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/access/country-sets";

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            HttpResponseMessage response = await client.GetAsync(url);

            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}

**Example response:**

```json
{
    "prefix": "_set-",
    "countrySets": [
        {
            "code": "courir",
            "name": "COURIR"
        },
        {
            "code": "mesh1",
            "name": "MESH 1"
        },
        {
            "code": "mesh2",
            "name": "MESH 2"
        },
        {
            "code": "nikeas",
            "name": "NIKE ASIA"
        },
        {
            "code": "nikeeu",
            "name": "NIKE EU"
        },
        {
            "code": "nikena",
            "name": "NIKE US"
        },
        {
            "code": "zalando",
            "name": "ZALANDO"
        }
    ]
}
```

## Generate Proxy List

<mark style="color:blue;">`POST`</mark>  `/access/generate-proxy-list`

{% hint style="info" %}
If **`subuser_hash`** is supplied, **`username`** and **`password`** are not needed, and vice versa - if **`username`** and **`password`** are supplied - **`subuser_hash`** is not needed.
{% endhint %}

{% hint style="info" %}
The location you wish to use needs to be prefixed with a "prefix" that is described in the [#get-countries](#get-countries "mention"), for example if you want to target Singapore - "**\_country-sg**"
{% endhint %}

**Body Parameters**

<table><thead><tr><th width="154">Name</th><th width="167">Type</th><th width="201">Description</th><th>Available options</th></tr></thead><tbody><tr><td>format</td><td>String</td><td>Format in which proxy strings will be returned</td><td><p></p><pre><code><strong>{hostname}:{port}:{username}:{password}
</strong>{hostname}:{port}@{username}:{password}
{username}:{password}:{hostname}:{port}
</code></pre></td></tr><tr><td>hostname</td><td>String</td><td>Hostname that will be used</td><td><a data-mention href="#entry-nodes">#entry-nodes</a></td></tr><tr><td>port</td><td>String</td><td>Port as protocol type</td><td><pre><code>http|https
socks5
</code></pre></td></tr><tr><td>rotation</td><td>String</td><td>Rotation that will be used</td><td><p></p><pre><code>sticky
random
</code></pre></td></tr><tr><td>subuser_hash</td><td>String</td><td>Subuser that will be used</td><td></td></tr><tr><td>location</td><td>String</td><td>Location that will be used</td><td><a data-mention href="#get-countries">#get-countries</a></td></tr><tr><td>proxy_count</td><td>Integer</td><td>Proxy count that will be returned</td><td></td></tr><tr><td>username</td><td>String</td><td>Username that will be used</td><td></td></tr><tr><td>password</td><td>String</td><td>Password that will be used</td><td></td></tr><tr><td>lifetime</td><td>String</td><td>For sticky sessions this will tell how long this session will last</td><td><pre><code>5s
10m
20h

</code></pre></td></tr></tbody></table>

**Example request:**&#x20;

{% tabs %}
{% tab title="cURL" %}

```
curl -X POST https://resi-api.iproyal.com/v1/access/generate-proxy-list \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <your_api_token>" \
     -d '{
           "format": "{hostname}:{port}:{username}:{password}",
           "hostname": "example.hostname.com",
           "port": "http|https",
           "rotation": "sticky",
           "location": "_country-sg",
           "proxy_count": 10,
           "subuser_hash": "example_subuser_hash",
           "lifetime": "2h"
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/access/generate-proxy-list';

$data = [
    'format' => '{hostname}:{port}:{username}:{password}',
    'hostname' => 'example.hostname.com',
    'port' => 'http|https',
    'rotation' => 'sticky',
    'location' => '_country-sg',
    'proxy_count' => 10,
    'subuser_hash' => 'example_subuser_hash'
];

$payload = json_encode($data);

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    "Authorization: Bearer $api_token"
]);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);

$response = curl_exec($ch);

if (curl_errno($ch)) {
    echo 'Error:' . curl_error($ch);
} else {
    echo $response;
}

curl_close($ch);
?>

```

{% endtab %}

{% tab title="Python" %}

```python
import requests

api_token = '<your_api_token>'
url = 'https://resi-api.iproyal.com/v1/access/generate-proxy-list'

data = {
    'format': '{hostname}:{port}:{username}:{password}',
    'hostname': 'example.hostname.com',
    'port': 'http|https',
    'rotation': 'sticky',
    'location': '_country-sg',
    'proxy_count': 10,
    'subuser_hash': 'example_subuser_hash'
}

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_token}'
}

response = requests.post(url, json=data, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';
const url = 'https://resi-api.iproyal.com/v1/access/generate-proxy-list';

const data = JSON.stringify({
  format: '{hostname}:{port}:{username}:{password}',
  hostname: 'example.hostname.com',
  port: 'http|https',
  rotation: 'sticky',
  location: '_country-sg',
  proxy_count: 10,
  subuser_hash: 'example_subuser_hash'
});

const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiToken}`
  }
};

const req = https.request(url, options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log(data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.write(data);
req.end();
```

{% endtab %}

{% tab title="Java" %}

```java
import java.io.OutputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiRequest {
    public static void main(String[] args) {
        String apiToken = "<your_api_token>";
        String urlString = "https://resi-api.iproyal.com/v1/access/generate-proxy-list";

        String requestBody = """
            {
                "format": "{hostname}:{port}:{username}:{password}",
                "hostname": "example.hostname.com",
                "port": "http|https",
                "rotation": "sticky",
                "location": "_country-sg",
                "proxy_count": 10,
                "subuser_hash": "example_subuser_hash",
                "lifetime": "2h"
            }
        """;

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiToken)
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        System.out.println(response.body());
    }
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
)

const (
	apiToken  = "<your_api_token>"
	proxyURL  = "https://resi-api.iproyal.com/v1/access/generate-proxy-list"
)

func main() {
	data := map[string]interface{}{
		"format":        "{hostname}:{port}:{username}:{password}",
		"hostname":      "example.hostname.com",
		"port":          "http|https",
		"rotation":      "sticky",
		"location":      "_country-sg",
		"proxy_count":   10,
		"subuser_hash":  "example_subuser_hash",
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		log.Fatal("Error marshaling JSON:", err)
	}

	req, err := http.NewRequest(http.MethodPost, proxyURL, bytes.NewBuffer(jsonData))
	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiToken)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatal("Error making request:", err)
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal("Error reading response body:", err)
	}

	fmt.Println(string(responseBody))
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System.Text;
using System.Text.Json;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/access/generate-proxy-list";

        var data = new
        {
            format = "{hostname}:{port}:{username}:{password}",
            hostname = "example.hostname.com",
            port = "http|https",
            rotation = "sticky",
            location = "_country-sg",
            proxy_count = 10,
            subuser_hash = "example_subuser_hash"
        };

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            var jsonData = JsonSerializer.Serialize(data);
            var content = new StringContent(jsonData, Encoding.UTF8, "application/json");

            HttpResponseMessage response = await client.PostAsync(url, content);

            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}

**Example response:**

```json
[
    "geo.iproyal.com:0:info@iproyal.com:royal123_session-abc123_lifetime-24h",
    "geo.iproyal.com:0:info@iproyal.com:royal123_session-cba321_lifetime-24h",
]
```
