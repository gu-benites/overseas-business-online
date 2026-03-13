# Orders

## Get Orders

<mark style="color:green;">`GET`</mark> `/residential/orders`

**Query Parameters**

| Name      | Type    | Description                      |
| --------- | ------- | -------------------------------- |
| page      | Integer | Number of page                   |
| per\_page | Integer | Number of orders to get per page |

#### Example request:

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET "https://resi-api.iproyal.com/v1/residential/orders?page=1&per_page=10" \
     -H "Authorization: Bearer <your_api_token>"
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/residential/orders?page=1&per_page=10';

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
url = 'https://resi-api.iproyal.com/v1/residential/orders?page=1&per_page=10'

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
const url = 'https://resi-api.iproyal.com/v1/residential/orders?page=1&per_page=10';

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
        String urlString = "https://resi-api.iproyal.com/v1/residential/orders?page=1&per_page=10";

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
	url    = "https://resi-api.iproyal.com/v1/residential/orders?page=1&per_page=10"
)

func main() {
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
        string url = "https://resi-api.iproyal.com/v1/residential/orders?page=1&per_page=10";

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

#### Example response:

```json
{
  "data": [
    {
      "id": 4,
      "note": null,
      "product_name": "Residential",
      "status": "confirmed",
      "amount": 50,
      "quantity": 10,
      "order_billing_type": "subscription",
      "created_at": "2025-06-26 10:01:50"
    }
  ],
  "meta": {
    "current_page": 1,
    "last_page": 1,
    "per_page": 20,
    "total": 1
  }
}
```

## Create Order

<mark style="color:blue;">`POST`</mark> `/residential/orders`

**Body Parameters:**

| Name                 | Type    | Description                                                                                              |
| -------------------- | ------- | -------------------------------------------------------------------------------------------------------- |
| quantity             | Integer | GB quantity                                                                                              |
| coupon\_code         | String  | A discount code to apply to the order, if available.                                                     |
| card\_id             | Integer | If supplied - card will be billed for this order, if not - we will try to deduct the amount from balance |
| order\_billing\_type | String  | `subscription` or `regular` default - `subscription`                                                     |

**Example request:**

{% tabs %}
{% tab title="cURL" %}

```
curl -X POST https://resi-api.iproyal.com/v1/residential/orders \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{"quantity": 10}'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';
$url = 'https://resi-api.iproyal.com/v1/residential/orders';

$data = ['quantity' => 10];

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
url = 'https://resi-api.iproyal.com/v1/residential/orders'

data = {'quantity': 10}

headers = {
    'Authorization': 'Bearer ' + api_token,
    'Content-Type': 'application/json'
}

response = requests.post(url, json=data, headers=headers)

print(response.status_code)
print(response.json())
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';

const data = JSON.stringify({quantity: 10});

const options = {
  hostname: 'resi-api.iproyal.com',
  path: '/v1/residential/orders',
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + apiToken,
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
        String accessToken = "<your_api_token>";
        String url = "https://resi-api.iproyal.com/v1/residential/orders";

        String requestBody = """
            {
                "quantity": 10
            }
        """;

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + accessToken)
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
    apiToken = "<your_api_token>"
    url      = "https://resi-api.iproyal.com/v1/residential/orders"
)

func main() {
    data := map[string]interface{}{
        "quantity": 10,
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
    
    var jsonResponse map[string]interface{}
    err = json.Unmarshal(responseBody, &jsonResponse)
    if err != nil {
        log.Fatal("Error unmarshaling JSON:", err)
    }
    
    fmt.Printf("%+v\n", jsonResponse)
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
        string url = "https://resi-api.iproyal.com/v1/residential/orders";

        var data = new
        {
            quantity = 10,
        };

        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", "Bearer " + apiToken);

            var jsonData = JsonSerializer.Serialize(data);
            var content = new StringContent(jsonData, Encoding.UTF8, "application/json");

            HttpResponseMessage response = await client.PostAsync(url, content);

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

**Response:**

```json
{
    "id": 4,
    "note": null,
    "product_name": "Residential",
    "status": "confirmed",
    "amount": 50,
    "quantity": 10,
    "order_billing_type": "subscription",
    "created_at": "2025-06-26 10:01:50"
}
```

## Calculate Pricing

<mark style="color:green;">`GET`</mark> `/residential/orders/calculate-pricing`

**Query Parameters:**

| Name                 | Type    | Description                                          |
| -------------------- | ------- | ---------------------------------------------------- |
| quantity             | Integer | Required. The amount of the product to order.        |
| coupon\_code         | String  | Optional. Discount code for the order.               |
| order\_billing\_type | String  | `subscription` or `regular` default - `subscription` |

#### Example request:

{% tabs %}
{% tab title="cURL" %}

```
curl -X GET https://resi-api.iproyal.com/v1/residential/orders/calculate-pricing \
     -H "Authorization: Bearer <your_api_token>" \
     -H "Content-Type: application/json" \
     -d '{"quantity": 10}'
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$api_token = '<your_api_token>';

$data = ['quantity' => 10];
$url = 'https://resi-api.iproyal.com/v1/residential/orders/calculate-pricing' . http_build_query($data);

$options = [
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        "Authorization: Bearer $api_token",
        'Content-Type: application/json'
    ],
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
url = 'https://resi-api.iproyal.com/v1/residential/orders/calculate-pricing'

data = {'quantity': 10}

headers = {
    'Authorization': 'Bearer ' + api_token,
    'Content-Type': 'application/json'
}

response = requests.get(url, json=data, headers=headers)

print(response.status_code)
print(response.json())
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const https = require('https');

const apiToken = '<your_api_token>';

const data = JSON.stringify({quantity: 10});

const options = {
  hostname: 'resi-api.iproyal.com',
  path: '/v1/residential/orders/calculate-pricing',
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + api_token,
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
        String accessToken = "<your_access_token>";
        Number quantity = 10;
        String url = "https://resi-api.iproyal.com/v1/residential/orders/calculate-pricing?quantity=" + quantity;

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + accessToken)
                .GET()
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
    apiToken = "<your_api_token>"
    url      = "https://resi-api.iproyal.com/v1/residential/orders/calculate-pricing"
)

func main() {
    data := map[string]interface{}{
        "quantity": 10,
    }
    
    jsonData, err := json.Marshal(data)
    if err != nil {
        log.Fatal("Error marshaling JSON:", err)
    }
    
    req, err := http.NewRequest(http.MethodGet, url, bytes.NewBuffer(jsonData))
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
    
    var jsonResponse map[string]interface{}
    err = json.Unmarshal(responseBody, &jsonResponse)
    if err != nil {
        log.Fatal("Error unmarshaling JSON:", err)
    }
    
    fmt.Printf("%+v\n", jsonResponse)
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
        string apiToken = "<your_api_key>";
        string baseUrl = "https://resi-api.iproyal.com/v1/residential/orders/calculate-pricing";
        int quantity = 10;
        string url = $"{baseUrl}?quantity={quantity}";
        
        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("Authorization", "Bearer " + apiToken);
            
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

#### Example response:

```json
{
  "total": 50
}
```
