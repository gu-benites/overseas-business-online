# Whitelists

The link provided below directs to a detailed page that elaborates on the concept of a whitelist within our system.

[ip-whitelisting](https://docs.iproyal.com/proxies/residential/proxy/ip-whitelisting "mention")

***

It's important to note that almost every endpoint related to whitelists, with the notable exceptions of the **`index`** and **`delete`** endpoints, will return a whitelist entry resource upon a successful call.

{% code title="WhitelistEntryResource" %}

```json
{
    "hash": "01HQ5K3P97DY8EX9Y90YT1K6XA",
    "ip": "192.0.2.1",
    "port": "23234",
    "type": "http|https",
    "configuration": "_country-br_streaming-1_skipispstatic-1"
}
```

{% endcode %}

***

## Create Whitelist Entry

<mark style="color:blue;">`POST`</mark>  `/residential-users/{ residential_user_hash }/whitelist-entries`

**Query Parameters**

<table><thead><tr><th width="234">Name</th><th width="246">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr></tbody></table>

**Body Parameters**

<table><thead><tr><th width="149">Name</th><th width="107">Type</th><th>Description</th></tr></thead><tbody><tr><td>ip</td><td>String</td><td>Ip of the entry</td></tr><tr><td>port</td><td>Integer</td><td>Port that will be used</td></tr><tr><td>configuration</td><td>String</td><td>Proxy configuration</td></tr><tr><td>note</td><td>String</td><td>Proxy note</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X POST "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/whitelist-entries" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{
           "ip": "192.168.1.1",
           "port": 8080,
           "configuration": "some_configuration"
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$residential_user_hash = '<residential_user_hash>';
$ip = '192.168.1.1';
$port = 8080;
$configuration = 'some_configuration';

$url = "https://resi-api.iproyal.com/v1/residential-users/$residential_user_hash/whitelist-entries";

$data = [
    'ip' => $ip,
    'port' => $port,
    'configuration' => $configuration
];

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
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/whitelist-entries'

data = {
    'ip': '192.168.1.1',
    'port': 8080,
    'configuration': 'some_configuration'
}

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.post(url, json=data, headers=headers)

print(response.status_code)
print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';
const ip = '192.168.1.1';
const port = 8080;
const configuration = 'some_configuration';
const data = JSON.stringify({ ip, port, configuration });

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/whitelist-entries`,
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
        String url = "https://resi-api.iproyal.com/v1/residential-users/" + residentialUserHash + "/whitelist-entries";

        String requestBody = """
            {
                "ip": "192.168.1.1",
                "port": 8080,
                "configuration": "some_configuration"
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
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/whitelist-entries", residentialUserHash)

	data := map[string]interface{}{
		"ip":            "192.168.1.1",
		"port":          8080,
		"configuration": "some_configuration",
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
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/whitelist-entries";

        var data = new
        {
            ip = "192.168.1.1",
            port = 8080,
            configuration = "some_configuration"
        };

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            var jsonData = JsonSerializer.Serialize(data);
            var content = new StringContent(jsonData, Encoding.UTF8, "application/json");

            HttpResponseMessage response = await client.PostAsync(url, content);

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
    "hash": "01JVRVH56YYVG2RZDFA123ABCD",
    "ip": "192.168.1.1",
    "port": 8080,
    "type": "?",
    "configuration": "some_configuration",
    "note": null
}
```

## Get Whitelist Entry

<mark style="color:green;">`GET`</mark>  `/residential-users/{ residential_user_hash }/whitelist-entries/{ whitelist_entry_hash }`

**Query Parameters**

<table><thead><tr><th width="234">Name</th><th width="246">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr><tr><td>whitelist_entry_hash</td><td>String</td><td>Hash of the entry</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/whitelist-entries/<whitelist_entry_hash>" \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$residential_user_hash = '<residential_user_hash>';
$whitelist_entry_hash = '<whitelist_entry_hash>';

$url = "https://resi-api.iproyal.com/v1/residential-users/$residential_user_hash/whitelist-entries/$whitelist_entry_hash";

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token"
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
whitelist_entry_hash = '<whitelist_entry_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/whitelist-entries/{whitelist_entry_hash}'

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

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';
const whitelist_entry_hash = '<whitelist_entry_hash>';

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/whitelist-entries/${whitelist_entry_hash}`,
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${api_token}`
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
        String whitelistEntryHash = "<whitelist_entry_hash>";
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-users/%s/whitelist-entries/%s", residentialUserHash, whitelistEntryHash);

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
	"fmt"
	"io"
	"log"
	"net/http"
)

const (
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
	whitelistEntryHash  = "<whitelist_entry_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/whitelist-entries/%s", residentialUserHash, whitelistEntryHash)

	req, err := http.NewRequest(http.MethodGet, url, nil)
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
        string residentialUserHash = "<residential_user_hash>";
        string whitelistEntryHash = "<whitelist_entry_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/whitelist-entries/{whitelistEntryHash}";

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

**Example response:**&#x20;

```json
{
    "hash": "01JVRVH56YYVG2RZDFA123ABCD",
    "ip": "192.168.1.1",
    "port": 8080,
    "type": "?",
    "configuration": "some_configuration",
    "note": null
}
```

## Get Whitelist Entries

<mark style="color:green;">`GET`</mark>  `/residential-users/{ residential_user_hash }/whitelist-entries/`

**Query Parameters**

<table><thead><tr><th width="222">Name</th><th width="104">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr><tr><td>page</td><td>Integer</td><td>Number of the page</td></tr><tr><td>per_page</td><td>Integer</td><td>Number of whitelist entries per page</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/whitelist-entries?page=<page>&per_page=<per_page>" \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$residential_user_hash = '<residential_user_hash>';
$page = 1;
$per_page = 10;

$url = "https://resi-api.iproyal.com/v1/residential-users/$residential_user_hash/whitelist-entries?page=$page&per_page=$per_page";

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token"
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
page = 1
per_page = 10
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/whitelist-entries?page={page}&per_page={per_page}'

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

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';
const page = 1;
const per_page = 10;

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/whitelist-entries?page=${page}&per_page=${per_page}`,
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${api_token}`
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
        int page = 1;
        int perPage = 10;
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-users/%s/whitelist-entries?page=%d&per_page=%d", residentialUserHash, page, perPage);

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
	"fmt"
	"io"
	"log"
	"net/http"
)

const (
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
	page                = 1
	perPage             = 10
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/whitelist-entries?page=%d&per_page=%d", residentialUserHash, page, perPage)

	req, err := http.NewRequest(http.MethodGet, url, nil)
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
        string residentialUserHash = "<residential_user_hash>";
        int page = 1;
        int perPage = 10;
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/whitelist-entries?page={page}&per_page={perPage}";

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

**Example response:**&#x20;

```json
{
    "data": [
        {
            "hash": "01JVRVH56YYVG2RZDFA123ABCD",
            "ip": "192.168.1.1",
            "port": 8080,
            "type": "?",
            "configuration": "some_configuration",
            "note": null
        }
    ],
    "meta": {
        "current_page": 1,
        "from": 1,
        "last_page": 1,
        "path": "/",
        "per_page": 20,
        "to": 1,
        "total": 1
    }
}
```

## Update Whitelist Entry

<mark style="color:orange;">`UPDATE`</mark>  `/residential-users/{ residential_user_hash }/whitelist-entries/{ whitelist_entry_hash }`

**Query Parameters**

<table><thead><tr><th width="229">Name</th><th width="104">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr><tr><td>whitelist_entry_hash</td><td>String</td><td>Hash of the entry</td></tr></tbody></table>

**Body Parameters**

<table><thead><tr><th width="156">Name</th><th width="107">Type</th><th>Description</th></tr></thead><tbody><tr><td>configuration</td><td>String</td><td>Proxy configuration</td></tr><tr><td>note</td><td>String</td><td>Proxy note</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X PUT "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/whitelist-entries/<whitelist_entry_hash>" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{
           "configuration": "updated_configuration"
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
import requests

api_token = '<your_api_token>'
residential_user_hash = '<residential_user_hash>'
whitelist_entry_hash = '<whitelist_entry_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/whitelist-entries/{whitelist_entry_hash}'

configuration = {
    'configuration': {}
}

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.put(url, json=configuration, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

api_token = '<your_api_token>'
residential_user_hash = '<residential_user_hash>'
whitelist_entry_hash = '<whitelist_entry_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/whitelist-entries/{whitelist_entry_hash}'

configuration = {
    'configuration': {}
}

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.put(url, json=configuration, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';
const whitelist_entry_hash = '<whitelist_entry_hash>';
const configuration = JSON.stringify({
  configuration: {}
});

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/whitelist-entries/${whitelist_entry_hash}`,
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${api_token}`,
    'Content-Type': 'application/json',
    'Content-Length': configuration.length
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

req.write(configuration);
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
        String whitelistEntryHash = "<whitelist_entry_hash>";
        String url = "https://resi-api.iproyal.com/v1/residential-users/" + residentialUserHash + "/whitelist-entries/" + whitelistEntryHash;

        String requestBody = """
            {
                "configuration": {}
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
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
	whitelistEntryHash  = "<whitelist_entry_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/whitelist-entries/%s", residentialUserHash, whitelistEntryHash)

	configuration := map[string]interface{}{
		"configuration": map[string]interface{}{},
	}

	jsonData, err := json.Marshal(configuration)
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
        string whitelistEntryHash = "<whitelist_entry_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/whitelist-entries/{whitelistEntryHash}";

        var configuration = new
        {
            configuration = ""
        };

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            var jsonData = JsonSerializer.Serialize(configuration);
            var content = new StringContent(jsonData, Encoding.UTF8, "application/json");

            HttpResponseMessage response = await client.PutAsync(url, content);

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
    "hash": "01JVRVH56YYVG2RZDFA123ABCD",
    "ip": "192.168.1.1",
    "port": 8080,
    "type": "?",
    "configuration": "updated_configuration",
    "note": null
}
```

## Delete Whitelist Entry

<mark style="color:red;">`DELETE`</mark>  `/residential-users/{ residential_user_hash }/whitelist-entries/{ whitelist_entry_hash }`

**Query Parameters**

<table><thead><tr><th width="234">Name</th><th width="246">Type</th><th>Description</th></tr></thead><tbody><tr><td>residential_user_hash</td><td>String</td><td>Hash of the user</td></tr><tr><td>whitelist_entry_hash</td><td>String</td><td>Hash of the entry</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X DELETE "https://resi-api.iproyal.com/v1/residential-users/<residential_user_hash>/whitelist-entries/<whitelist_entry_hash>" \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$residential_user_hash = '<residential_user_hash>';
$whitelist_entry_hash = '<whitelist_entry_hash>';

$url = "https://resi-api.iproyal.com/v1/residential-users/$residential_user_hash/whitelist-entries/$whitelist_entry_hash";

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CUSTOMREQUEST => 'DELETE',
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token"
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
whitelist_entry_hash = '<whitelist_entry_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-users/{residential_user_hash}/whitelist-entries/{whitelist_entry_hash}'

headers = {
    'Authorization': f'Bearer {api_token}'
}

response = requests.delete(url, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const api_token = '<your_api_token>';
const residential_user_hash = '<residential_user_hash>';
const whitelist_entry_hash = '<whitelist_entry_hash>';

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-users/${residential_user_hash}/whitelist-entries/${whitelist_entry_hash}`,
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${api_token}`
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
        String whitelistEntryHash = "<whitelist_entry_hash>";
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-users/%s/whitelist-entries/%s", residentialUserHash, whitelistEntryHash);

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("DELETE");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);

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
	"io"
	"log"
	"net/http"
)

const (
	apiToken            = "<your_api_token>"
	residentialUserHash = "<residential_user_hash>"
	whitelistEntryHash  = "<whitelist_entry_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-users/%s/whitelist-entries/%s", residentialUserHash, whitelistEntryHash)

	req, err := http.NewRequest(http.MethodDelete, url, nil)
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
        string residentialUserHash = "<residential_user_hash>";
        string whitelistEntryHash = "<whitelist_entry_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-users/{residentialUserHash}/whitelist-entries/{whitelistEntryHash}";

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");

            HttpResponseMessage response = await client.DeleteAsync(url);

            string responseText = await response.Content.ReadAsStringAsync();
            Console.WriteLine(responseText);
        }
    }
}
```

{% endtab %}
{% endtabs %}
