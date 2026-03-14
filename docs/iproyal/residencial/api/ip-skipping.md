# IP Skipping

The link provided below directs to a detailed page that elaborates on the concept of IP skipping within our system.

[ip-skipping](https://docs.iproyal.com/proxies/residential/proxy/ip-skipping "mention")

***

It's important to note that almost every endpoint related to IP skipping, with the notable exceptions of the **`index`** and **`delete`** endpoints, will return an IP skipping resource upon a successful call.

{% code title="IpSkippingResource" %}

```json
{
    "hash": "01HQ5K3P97DY8EX9Y90YT1K6XA",
    "title": "192.0.2.1",
    "items": [
        {
            "hash": "01HQJ5GS1NXBP562CCQFQB6XN7",
            "ip_range": "24.52.81.2/32"
        },
        {
            "hash": "01HQJ5GW9NXBCC62CCQFQB6XN7",
            "ip_range": "14.51.82.2/32"
        }
    ]
}
```

{% endcode %}

***

## Create IP Skipping List

<mark style="color:blue;">`POST`</mark>  `/residential-users/{residential_user_hash}/ips-skipping`

**Query Parameters**

<table><thead><tr><th width="234">Name</th><th width="246">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr></tbody></table>

**Body Parameters**

<table><thead><tr><th width="232">Name</th><th width="107">Type</th><th>Description</th></tr></thead><tbody><tr><td>title</td><td>String</td><td>Title of the IP skipping list</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X POST "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/ips-skipping" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{
           "title": "Your Title"
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$residential_user_hash = '<residential_user_hash>';
$title = 'Your Title';

$url = "https://resi-api.iproyal.com/v1/residential-users/$residential_user_hash/ips-skipping";

$data = ['title' => $title];

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token",
        'Content-Type: application/json'
    ],
    CURLOPT_POSTFIELDS => json_encode($data)
];

$ch = curl_init();
curl_setopt_array($ch, $options);
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
residential_user_hash = '<residential_user_hash>'
title = 'Your Title'
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/ips-skipping'

data = {
    'title': title
}

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.post(url, json=data, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';
const title = 'Your Title';

const data = JSON.stringify({
  title: title
});

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/ips-skipping`,
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${api_token}`,
    'Content-Type': 'application/json',
    'Content-Length': data.length
  }
};

const req = https.request(options, (res) => {
  let responseData = '';

  res.on('data', (chunk) => {
    responseData += chunk;
  });

  res.on('end', () => {
    console.log(responseData);
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
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class Main {
    public static void main(String[] args) throws Exception {
        String apiToken = "<your_api_token>";
        String residentialUserHash = "<residential_user_hash>";
        String url = "https://resi-api.iproyal.com/v1/residential-users/" + residentialUserHash + "/ips-skipping";

        String requestBody = """
            {
                "title": "Your Title"
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

        System.out.println("Response Code: " + response.statusCode());
        System.out.println("Response Body: " + response.body());
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
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
	title               = "Your Title"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/ips-skipping", residentialUserHash)

	data := map[string]interface{}{
		"title": title,
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		log.Fatal("Error marshaling JSON:", err)
	}

	req, err := http.NewRequest(http.MethodPost, url, bytes.NewBuffer(jsonData))
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
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string residentialUserHash = "<residential_user_hash>";
        string title = "Your Title";
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/ips-skipping";

        var data = new
        {
            title = title
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

**Example response:**&#x20;

```json
{
    "hash": "01HQ5K3P97DY8EX9Y90YT1K6XA",
    "title": "Your Title",
    "items": [
        {
            "hash": "01HQJ5GS1NXBP562CCQFQB6XN7",
            "ip_range": "24.52.81.2/32"
        },
        {
            "hash": "01HQJ5GW9NXBCC62CCQFQB6XN7",
            "ip_range": "14.51.82.2/32"
        }
    ]
}
```

## Get IP Skipping Lists

<mark style="color:green;">`GET`</mark>  `/residential-users/{residential_user_hash}/ips-skipping`

**Query Parameters**

<table><thead><tr><th width="222">Name</th><th width="104">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/ips-skipping" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$residential_user_hash = '<residential_user_hash>';

$url = "https://resi-api.iproyal.com/v1/residential-users/$residential_user_hash/ips-skipping";

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token",
        'Content-Type: application/json'
    ]
];

$ch = curl_init();
curl_setopt_array($ch, $options);
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
residential_user_hash = '<residential_user_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/ips-skipping'

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.get(url, headers=headers)

print(response.status_code)
print(response.json())
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/ips-skipping`,
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${api_token}`,
    'Content-Type': 'application/json'
  }
};

const req = https.request(options, (res) => {
  let responseData = '';

  res.on('data', (chunk) => {
    responseData += chunk;
  });

  res.on('end', () => {
    console.log(responseData);
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
        String residentialUserHash = "<residential_user_hash>";
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-users/%s/ips-skipping", residentialUserHash);

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);
            connection.setRequestProperty("Content-Type", "application/json");

            int responseCode = connection.getResponseCode();
            System.out.println("Response Code: " + responseCode);

            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                String inputLine;
                StringBuilder content = new StringBuilder();

                while ((inputLine = in.readLine()) != null) {
                    content.append(inputLine);
                }
                in.close();

                System.out.println("Response Body: " + content.toString());
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
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
)

const (
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/ips-skipping", residentialUserHash)

	req, err := http.NewRequest(http.MethodGet, url, nil)
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

	fmt.Println("Status Code:", resp.StatusCode)

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal("Error reading response body:", err)
	}

	fmt.Printf(string(responseBody))
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string residentialUserHash = "<residential_user_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/ips-skipping";

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            HttpResponseMessage response = await client.GetAsync(url);

            Console.WriteLine((int)response.StatusCode);

            string responseText = await response.Content.ReadAsStringAsync();
            var jsonResponse = JsonSerializer.Deserialize<JsonElement>(responseText);
            Console.WriteLine(jsonResponse);
        }
    }
}
```

{% endtab %}
{% endtabs %}

**Example response:**&#x20;

```json
{
    "data": [
        {
            "hash": "01HQ5K3P97DY8EX9Y90YT1K6XA",
            "title": "Your Title",
            "items": [
                {
                    "hash": "01HQJ5GS1NXBP562CCQFQB6XN7",
                    "ip_range": "24.52.81.2/32"
                },
                {
                    "hash": "01HQJ5GW9NXBCC62CCQFQB6XN7",
                    "ip_range": "14.51.82.2/32"
                }
            ]
        }
    ],
    "meta": {
        "current_page": 1,
        "from": 1,
        "last_page": 1,
        "path": "/",
        "per_page": 15,
        "to": 1,
        "total": 1
    }
}
```

## Update IP Skipping List

<mark style="color:orange;">`UPDATE`</mark>  `/residential-users/{residential_user_hash}/ips-skipping/{ips_skipping_hash}`

**Query Parameters**

<table><thead><tr><th width="229">Name</th><th width="104">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr><tr><td>ips_skipping_hash</td><td>String</td><td>Hash of the IPs skipping list</td></tr></tbody></table>

**Body Parameters**

<table><thead><tr><th width="156">Name</th><th width="107">Type</th><th>Description</th></tr></thead><tbody><tr><td>title</td><td>String</td><td>Title of the skipping list</td></tr><tr><td>ip_ranges</td><td>Array</td><td>Ranges to be added to the list</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X PUT "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/ips-skipping/<ips_skipping_hash>" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{
           "title": "New Title",
           "ip_ranges": ["192.168.0.0/24", "10.0.0.0/8"]
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$residential_user_hash = '<residential_user_hash>';
$ips_skipping_hash = '<ips_skipping_hash>';
$title = 'New Title';
$ip_ranges = ['192.168.0.0/24', '10.0.0.0/8'];

$url = "https://resi-api.iproyal.com/v1/residential-users/$residential_user_hash/ips-skipping/$ips_skipping_hash";

$data = [
    'title' => $title,
    'ip_ranges' => $ip_ranges
];

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CUSTOMREQUEST => 'PUT',
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token",
        'Content-Type: application/json'
    ],
    CURLOPT_POSTFIELDS => json_encode($data)
];

$ch = curl_init();
curl_setopt_array($ch, $options);
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
residential_user_hash = '<residential_user_hash>'
ips_skipping_hash = '<ips_skipping_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/ips-skipping/{ips_skipping_hash}'

data = {
    'title': 'New Title',
    'ip_ranges': ['192.168.0.0/24', '10.0.0.0/8']
}

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.put(url, json=data, headers=headers)

print(response.status_code)
print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';
const ips_skipping_hash = '<ips_skipping_hash>';
const title = 'New Title';
const ip_ranges = ['192.168.0.0/24', '10.0.0.0/8'];
const data = JSON.stringify({ title, ip_ranges });

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/ips-skipping/${ips_skipping_hash}`,
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${api_token}`,
    'Content-Type': 'application/json',
    'Content-Length': data.length
  }
};

const req = https.request(options, (res) => {
  let responseData = '';

  res.on('data', (chunk) => {
    responseData += chunk;
  });

  res.on('end', () => {
    console.log(responseData);
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
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class Main {
    public static void main(String[] args) throws Exception {
        String apiToken = "<your_api_token>";
        String residentialUserHash = "<residential_user_hash>";
        String ipsSkippingHash = "<ips_skipping_hash>";
        String url = "https://resi-api.iproyal.com/v1/residential-users/" + residentialUserHash + "/ips-skipping/" + ipsSkippingHash;

        String requestBody = """
            {
                "title": "New Title",
                "ip_ranges": ["192.168.0.0/24", "10.0.0.0/8"]
            }
        """;

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiToken)
                .PUT(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        System.out.println("Response Code: " + response.statusCode());
        System.out.println("Response Body: " + response.body());
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
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
	ipsSkippingHash     = "<ips_skipping_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/ips-skipping/%s", residentialUserHash, ipsSkippingHash)

	data := map[string]interface{}{
		"title":     "New Title",
		"ip_ranges": []string{"192.168.0.0/24", "10.0.0.0/8"},
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		log.Fatal("Error marshaling JSON:", err)
	}

	req, err := http.NewRequest(http.MethodPut, url, bytes.NewBuffer(jsonData))
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

	fmt.Println("Status Code:", resp.StatusCode)

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
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string residentialUserHash = "<residential_user_hash>";
        string ipsSkippingHash = "<ips_skipping_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/ips-skipping/{ipsSkippingHash}";

        var data = new
        {
            title = "New Title",
            ip_ranges = new string[] { "192.168.0.0/24", "10.0.0.0/8" }
        };

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            var jsonData = JsonSerializer.Serialize(data);
            var content = new StringContent(jsonData, Encoding.UTF8, "application/json");

            HttpResponseMessage response = await client.PutAsync(url, content);

            Console.WriteLine((int)response.StatusCode);
            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}

```

{% endtab %}
{% endtabs %}

**Example response:**&#x20;

```json
{
    "hash": "01HQ5K3P97DY8EX9Y90YT1K6XA",
    "title": "New Title",
    "items": [
        {
            "hash": "01HQJ5GS1NXBP562CCQFQB6XN7",
            "ip_range": "192.168.0.0/24"
        },
        {
            "hash": "01HQJ5GW9NXBCC62CCQFQB6XN7",
            "ip_range": "10.0.0.0/8"
        }
    ]
}
```

## Delete IP Skipping List

<mark style="color:red;">`DELETE`</mark>  `/residential-users/{residential_user_hash}/ips-skipping/{ips_skipping_hash}`

**Query Parameters**

<table><thead><tr><th width="234">Name</th><th width="246">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr><tr><td>ips_skipping_hash</td><td>String</td><td>Hash of the IPs skipping list</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X DELETE "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/ips-skipping/<ips_skipping_hash>" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$residential_user_hash = '<residential_user_hash>';
$ips_skipping_hash = '<ips_skipping_hash>';

$url = "https://resi-api.iproyal.com/v1/residential-users/$residential_user_hash/ips-skipping/$ips_skipping_hash";

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CUSTOMREQUEST => 'DELETE',
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token",
        'Content-Type: application/json'
    ]
];

$ch = curl_init();
curl_setopt_array($ch, $options);
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
residential_user_hash = '<residential_user_hash>'
ips_skipping_hash = '<ips_skipping_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/ips-skipping/{ips_skipping_hash}'

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.delete(url, headers=headers)

print(response.status_code)
print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';
const ips_skipping_hash = '<ips_skipping_hash>';

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/ips-skipping/${ips_skipping_hash}`,
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${api_token}`,
    'Content-Type': 'application/json'
  }
};

const req = https.request(options, (res) => {
  let responseData = '';

  res.on('data', (chunk) => {
    responseData += chunk;
  });

  res.on('end', () => {
    console.log(responseData);
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
        String residentialUserHash = "<residential_user_hash>";
        String ipsSkippingHash = "<ips_skipping_hash>";
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-users/%s/ips-skipping/%s", residentialUserHash, ipsSkippingHash);

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("DELETE");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);
            connection.setRequestProperty("Content-Type", "application/json");

            int responseCode = connection.getResponseCode();
            System.out.println("Response Code: " + responseCode);

            if (responseCode == HttpURLConnection.HTTP_OK || responseCode == HttpURLConnection.HTTP_NO_CONTENT) {
                BufferedReader in = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                String inputLine;
                StringBuilder content = new StringBuilder();

                while ((inputLine = in.readLine()) != null) {
                    content.append(inputLine);
                }
                in.close();

                System.out.println("Response Body: " + content.toString());
            } else {
                System.out.println("DELETE request failed. Response Code: " + responseCode);
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
	"fmt"
	"log"
	"net/http"
)

const (
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
	ipsSkippingHash     = "<ips_skipping_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/ips-skipping/%s", residentialUserHash, ipsSkippingHash)

	req, err := http.NewRequest(http.MethodDelete, url, nil)
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

	fmt.Println("Status Code:", resp.StatusCode)
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
        string residentialUserHash = "<residential_user_hash>";
        string ipsSkippingHash = "<ips_skipping_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/ips-skipping/{ipsSkippingHash}";

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            HttpResponseMessage response = await client.DeleteAsync(url);

            Console.WriteLine((int)response.StatusCode);
            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}
