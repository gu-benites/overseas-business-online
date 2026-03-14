# Sub-Users

The link provided below directs to a page that elaborates on the concept of a sub-user within our system.

[sub-users](https://docs.iproyal.com/proxies/residential/sub-users "mention")

***

It's important to note that almost every endpoint related to sub-users, with the notable exceptions of the **`index`** and **`delete`** endpoints, will return a Subuser resource upon a successful call.

{% code title="SubuserResource" %}

```json
{
    "id": 5,
    "hash": "01HQ5K3P97DY8EX9Y90YT1K6XA",
    "username": "subuser_231",
    "password": "asffqwv2f3w4214v",
    "traffic_available": 0.25,
    "traffic_used": 0
}
```

{% endcode %}

{% hint style="warning" %}
Note that you should not use the **`id`** field. It is a legacy field that will be removed in the future.
{% endhint %}

***

{% hint style="info" %}
When adding traffic to a sub-user through creation or updating, the traffic will be taken from the main account. Likewise, when you delete a sub-user or take traffic from a sub-user - it will be returned to the main user.
{% endhint %}

***

## Create Sub-User

<mark style="color:blue;">`POST`</mark>  `/residential-subusers`

**Body Parameters**

<table><thead><tr><th width="142">Name</th><th width="107">Type</th><th>Description</th></tr></thead><tbody><tr><td>username</td><td>String</td><td>username of the subuser</td></tr><tr><td>password</td><td>String</td><td>password of the subuser</td></tr><tr><td>traffic</td><td>Float</td><td>traffic (GB) that will be assigned to the subuser</td></tr><tr><td>limits</td><td>Array</td><td><p>optional parameter to define limits that will be assigned to the subuser. The structure may consist of the following keys: daily_limit, monthly_limit, and/or lifetime_limit.</p><pre><code>"limits": {                 
                 "daily_limit": 5000,
                 "monthly_limit": 150000,
                 "lifetime_limit": 1000000
}
</code></pre></td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X POST https://resi-api.iproyal.com/v1/residential-subusers \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <your_api_token>" \
     -d '{
           "username": "subuser123",
           "password": "securepassword",
           "traffic": 10.0,
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/residential-subusers';

$data = [
    'username' => 'subuser123',
    'password' => 'securepassword',
    'traffic' => 10.0
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
url = 'https://resi-api.iproyal.com/v1/residential-subusers'

data = {
    'username': 'subuser123',
    'password': 'securepassword',
    'traffic': 10.0
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
const url = 'https://resi-api.iproyal.com/v1/residential-subusers';

const data = JSON.stringify({
  username: 'subuser123',
  password: 'securepassword',
  traffic: 10.0
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
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class Main {
    public static void main(String[] args) throws Exception {
        String apiToken = "<your_api_token>";
        String url = "https://resi-api.iproyal.com/v1/residential-subusers";

        String requestBody = """
            {
                "username": "subuser123",
                "password": "securepassword",
                "traffic": 10.0
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
	"io"
	"log"
	"net/http"
	"fmt"
)

const (
	apiToken          = "<your_api_token>"
	residentialSubusersURL = "https://resi-api.iproyal.com/v1/residential-subusers"
)

func main() {
	data := map[string]interface{}{
		"username": "subuser123",
		"password": "securepassword",
		"traffic":  10.0,
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		log.Fatal("Error marshaling JSON:", err)
	}

	req, err := http.NewRequest(http.MethodPost, residentialSubusersURL, bytes.NewBuffer(jsonData))
	if err != nil {
		log.Fatal("Error creating request:", err)
	}

	req.Header.Set("Content-Type", "application/json")
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
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        string apiToken = "<your_api_token>";
        string url = "https://resi-api.iproyal.com/v1/residential-subusers";

        var data = new
        {
            username = "subuser123",
            password = "securepassword",
            traffic = 10.0
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
    "id": 5,
    "hash": "02JVRQ5BF83PTW19G1SRD955J0",
    "username": "subuser123",
    "password": "securepassword",
    "traffic_available": 10,
    "traffic_used": 0
}
```

## Get Sub-User

<mark style="color:green;">`GET`</mark>  `/residential-subusers/{ hash }`

**Query Parameters**

<table><thead><tr><th width="234">Name</th><th width="246">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>hash</code></td><td>String</td><td>hash of the subuser</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET "https://resi-api.iproyal.com/v1/residential-subusers/<subuser_hash>" \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = "https://resi-api.iproyal.com/v1/residential-subusers/{hash}";

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "Authorization: Bearer $api_token"
]);

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
hash = '<subuser_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-subusers/{hash}'

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
const hash = '<subuser_hash>';
const url = `https://resi-api.iproyal.com/v1/residential-subusers/${hash}`;

const options = {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${api_token}`
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
        String subuserHash = "<subuser_hash>";
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-subusers/%s", subuserHash);

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
	subuserHash = "<subuser_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-subusers/%s", subuserHash)

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
        string hash = "<subuser_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-subusers/{hash}";

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
    "id": 5,
    "hash": "02JVRQ5BF83PTW19G1SRD955J0",
    "username": "subuser123",
    "password": "securepassword",
    "traffic_available": 10,
    "traffic_used": 0
}
```

## Get Sub-Users

<mark style="color:green;">`GET`</mark>  `/residential-subusers`

**Query Parameters**

<table><thead><tr><th width="134">Name</th><th width="104">Type</th><th>Description</th></tr></thead><tbody><tr><td>page</td><td>Integer</td><td>Number of the page</td></tr><tr><td>per_page</td><td>Integer</td><td>Number of subusers per page</td></tr><tr><td>search</td><td>String</td><td>Search that will be used to filter subusers by username</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET "https://resi-api.iproyal.com/v1/residential-subusers?page=1&per_page=10&search=username_search" \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$page = 1;
$per_page = 10;
$search = 'username_search';

$url = "https://resi-api.iproyal.com/v1/residential-subusers?page=$page&per_page=$per_page&search=$search";

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "Authorization: Bearer $api_token"
]);

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
page = 1
per_page = 10
search = 'username_search'

url = f'https://resi-api.iproyal.com/v1/residential-subusers?page={page}&per_page={per_page}&search={search}'

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
const page = 1;
const per_page = 10;
const search = 'username_search';

const url = `https://resi-api.iproyal.com/v1/residential-subusers?page=${page}&per_page=${per_page}&search=${search}`;

const options = {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${api_token}`
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
        int page = 1;
        int perPage = 10;
        String search = "username_search";

        String urlString = String.format(
            "https://resi-api.iproyal.com/v1/residential-subusers?page=%d&per_page=%d&search=%s", 
            page, perPage, search
        );

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
	apiToken = "<your_api_token>"
	page     = 1
	perPage  = 10
	search   = "username_search"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-subusers?page=%d&per_page=%d&search=%s", page, perPage, search)

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
        int page = 1;
        int perPage = 10;
        string search = "username_search";
        string url = $"https://resi-api.iproyal.com/v1/residential-subusers?page={page}&per_page={perPage}&search={search}";

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
            "id": 5,
            "hash": "02JVRQ5BF83PTW19G1SRD955J0",
            "username": "subuser123",
            "password": "securepassword",
            "traffic_available": 10,
            "traffic_used": 0
        }
    ],
    "meta": {
        "current_page": 1,
        "from": 1,
        "last_page": 1,
        "path": "https://resi-api.iproyal.com/v1/residential-subusers",
        "per_page": 20,
        "to": 1,
        "total": 1
    }
}
```

## Update Sub-User

<mark style="color:orange;">`UPDATE`</mark>  `/residential-subusers/{ hash }`

**Query Parameters**

<table><thead><tr><th width="178">Name</th><th width="112">Type</th><th>Description</th></tr></thead><tbody><tr><td>hash</td><td>String</td><td>hash of the subuser</td></tr></tbody></table>

**Body Parameters**

<table><thead><tr><th width="173">Name</th><th width="122">Type</th><th>Description</th></tr></thead><tbody><tr><td>username</td><td>String</td><td>username of the subuser</td></tr><tr><td>password</td><td>String</td><td>password of the subuser</td></tr><tr><td>traffic</td><td>Float</td><td>traffic (GB) that will be assigned to the subuser</td></tr><tr><td>limits</td><td>Array</td><td><p>optional parameter to define limits that will be assigned to the subuser. The structure may consist of the following keys: daily_limit, monthly_limit, and/or lifetime_limit.</p><pre><code>"limits": {                 
                 "daily_limit": 5000,
                 "monthly_limit": 150000,
                 "lifetime_limit": 1000000
}
</code></pre></td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X PUT "https://resi-api.iproyal.com/v1/residential-subusers/<subuser_hash>" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{
           "username": "new_username",
           "password": "new_password",
           "traffic": 5.0
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$hash = '<subuser_hash>';
$username = 'new_username';
$password = 'new_password';
$traffic = 5.0;

$url = "https://resi-api.iproyal.com/v1/residential-subusers/$hash";

$data = [
    'username' => $username,
    'password' => $password,
    'traffic' => $traffic
];

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CUSTOMREQUEST => 'UPDATE',
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
hash = '<subuser_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-subusers/{hash}'

data = {
    'username': 'new_username',
    'password': 'new_password',
    'traffic': 5.0
}

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

response = requests.put(url, json=data, headers=headers)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const api_token = '<your_api_token>';
const hash = '<subuser_hash>';
const data = JSON.stringify({
  username: 'new_username',
  password: 'new_password',
  traffic: 5.0
});

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-subusers/${hash}`,
  method: 'UPDATE',
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
        String subuserHash = "<subuser_hash>";
        String url = "https://resi-api.iproyal.com/v1/residential-subusers/" + subuserHash;

        String requestBody = """
            {
                "username": "new_username",
                "password": "new_password",
                "traffic": 5.0
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
	apiToken    = "<your_api_token>"
	subuserHash = "<subuser_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-subusers/%s", subuserHash)

	data := map[string]interface{}{
		"username": "new_username",
		"password": "new_password",
		"traffic":  5.0,
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
        string hash = "<subuser_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-subusers/{hash}";

        var data = new
        {
            username = "new_username",
            password = "new_password",
            traffic = 5.0
        };

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiToken}");
            var jsonData = JsonSerializer.Serialize(data);
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
    "id": 5,
    "hash": "02JVRQ5BF83PTW19G1SRD955J0",
    "username": "new_username",
    "password": "new_password",
    "traffic_available": 5,
    "traffic_used": 0
}
```

## Delete Sub-User

<mark style="color:red;">`DELETE`</mark>  `/residential-subusers/{ hash }`

**Query Parameters**

<table><thead><tr><th width="234">Name</th><th width="246">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>hash</code></td><td>String</td><td>hash of the subuser</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X DELETE "https://resi-api.iproyal.com/v1/residential-subusers/<subuser_hash>" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$hash = '<subuser_hash>';

$url = "https://resi-api.iproyal.com/v1/residential-subusers/$hash";

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
hash = '<subuser_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-subusers/{hash}'

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
const hash = '<subuser_hash>';

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-subusers/${hash}`,
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
        String subuserHash = "<subuser_hash>";
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-subusers/%s", subuserHash);

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
	apiToken    = "<your_api_token>"
	subuserHash = "<subuser_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-subusers/%s", subuserHash)

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

	responseBody := new(bytes.Buffer)
	_, err = responseBody.ReadFrom(resp.Body)
	if err != nil {
		log.Fatal("Error reading response body:", err)
	}

	fmt.Println(responseBody.String())
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
        string hash = "<subuser_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-subusers/{hash}";

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

## Add Traffic to Sub-User

<mark style="color:blue;">`POST`</mark>  `/residential-subusers/{ hash }/give-traffic`

**Query Parameters**

<table><thead><tr><th width="234">Name</th><th width="246">Type</th><th>Description</th></tr></thead><tbody><tr><td><code>hash</code></td><td>String</td><td>hash of the subuser</td></tr></tbody></table>

**Body Parameters**

<table><thead><tr><th width="142">Name</th><th width="107">Type</th><th>Description</th></tr></thead><tbody><tr><td>amount</td><td>Float</td><td>amount of traffic (GB) to give</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X POST "https://resi-api.iproyal.com/v1/residential-subusers/<subuser_hash>/give-traffic" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{
           "amount": 5.0
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$hash = '<subuser_hash>';
$amount = 5.0;

$url = "https://resi-api.iproyal.com/v1/residential-subusers/$hash/give-traffic";

$data = [
    'amount' => $amount
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
hash = '<subuser_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-subusers/{hash}/give-traffic'

data = {
    'amount': 5.0
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
const hash = '<subuser_hash>';
const amount = 5.0;
const data = JSON.stringify({ amount });

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-subusers/${hash}/give-traffic`,
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
import java.io.OutputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiRequest {
    public static void main(String[] args) {
        String apiToken = "<your_api_token>";
        String subuserHash = "<subuser_hash>";
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-subusers/%s/give-traffic", subuserHash);

        String jsonData = String.format("{\"amount\": %s}", 5.0);

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setDoOutput(true);

            OutputStream os = connection.getOutputStream();
            os.write(jsonData.getBytes());
            os.flush();
            os.close();

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
                System.out.println("POST request failed. Response Code: " + responseCode);
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
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
)

const (
	apiToken    = "<your_api_token>"
	subuserHash = "<subuser_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-subusers/%s/give-traffic", subuserHash)

	data := map[string]interface{}{
		"amount": 5.0,
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
        string hash = "<subuser_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-subusers/{hash}/give-traffic";

        var data = new
        {
            amount = 5.0
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
    "id": 5,
    "hash": "02JVRQ5BF83PTW19G1SRD955J0",
    "username": "new_username",
    "password": "new_password",
    "traffic_available": 15,
    "traffic_used": 0
}
```

## Take Traffic From Sub-User

<mark style="color:blue;">`POST`</mark>  `/residential-subusers/{ hash }/take-traffic`

**Query Parameters**

<table><thead><tr><th width="134">Name</th><th width="104">Type</th><th>Description</th></tr></thead><tbody><tr><td>hash</td><td>String</td><td>hash of the subuser</td></tr></tbody></table>

**Body Parameters**

<table><thead><tr><th width="142">Name</th><th width="107">Type</th><th>Description</th></tr></thead><tbody><tr><td>amount</td><td>Float</td><td>amount of traffic (GB) to give</td></tr></tbody></table>

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X POST "https://resi-api.iproyal.com/v1/residential-subusers/<subuser_hash>/take-traffic" \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{
           "amount": 5.0
         }'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$hash = '<subuser_hash>';
$amount = 5.0;

$url = "https://resi-api.iproyal.com/v1/residential-subusers/$hash/take-traffic";

$data = [
    'amount' => $amount
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
hash = '<subuser_hash>'
url = f'https://resi-api.iproyal.com/v1/residential-subusers/{hash}/take-traffic'

data = {
    'amount': 5.0
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
const hash = '<subuser_hash>';
const amount = 5.0;
const data = JSON.stringify({ amount });

const options = {
  hostname: 'resi-api.iproyal.com',
  path: `/v1/residential-subusers/${hash}/take-traffic`,
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
import java.io.OutputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiRequest {
    public static void main(String[] args) {
        String apiToken = "<your_api_token>";
        String subuserHash = "<subuser_hash>";
        String urlString = String.format("https://resi-api.iproyal.com/v1/residential-subusers/%s/take-traffic", subuserHash);

        String jsonData = String.format("{\"amount\": %s}", 5.0);

        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Authorization", "Bearer " + apiToken);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setDoOutput(true);

            OutputStream os = connection.getOutputStream();
            os.write(jsonData.getBytes());
            os.flush();
            os.close();

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
                System.out.println("POST request failed. Response Code: " + responseCode);
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
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
)

const (
	apiToken    = "<your_api_token>"
	subuserHash = "<subuser_hash>"
)

func main() {
	url := fmt.Sprintf("https://resi-api.iproyal.com/v1/residential-subusers/%s/take-traffic", subuserHash)

	data := map[string]interface{}{
		"amount": 5.0,
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
        string hash = "<subuser_hash>";
        string url = $"https://resi-api.iproyal.com/v1/residential-subusers/{hash}/take-traffic";

        var data = new
        {
            amount = 5.0
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
    "id": 5,
    "hash": "02JVRQ5BF83PTW19G1SRD955J0",
    "username": "new_username",
    "password": "new_password",
    "traffic_available": 10,
    "traffic_used": 0
}
```
