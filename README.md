# Odin

Decentralized Federated File Hosting Platform
## Overview

Odin is an early alpha-stage decentralized federated file hosting platform designed to offer a scalable, user-friendly solution for sharing and accessing files across a distributed network. It merges the benefits of decentralization and federation to create a dynamic and resilient file-sharing ecosystem.

## Installation
To run Odin on your machine, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/4rtemis-4rrow/Odin.git

   cd Odin

2. **Activate the virtual environment**:
   
   On macOS and Linux:
   ```bash
   source .venv/bin/activate
   ```

   On Windows:
   ```bash
   .venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt

4. **Run the application:***:
   ```bash
   python Odin.py
## Key Features

Decentralized Hosting: Operates on a distributed network of nodes, each contributing to the overall system, ensuring robustness and redundancy.

Federated Architecture: Nodes communicate and interact seamlessly, enabling users to access files hosted on any participating node.

Admin-Only Uploads: File uploads are restricted to administrators. Uploads are done by manually placing files into designated directories rather than through a web interface.

Automatic Categorization: Files are automatically categorized based on their path and file extension, simplifying file organization and retrieval.

HTTP Access: Files can be accessed via standard HTTP, allowing users to browse and download files using any web browser without the need for specialized clients, unlike torrents.

Ease of Setup: Designed for simplicity, Odin is extremely easy to set up, requiring minimal configuration and maintenance.

## How It Works

Setup: Configure Odin by pointing it to a specific directory on your system. Odin will begin hosting files from this directory immediately.

File Access: Users can search and download files from any node in the network using a standard web browser. The federated design ensures that files are available across the network.

File Management: Administrators manage file uploads by manually placing files into the appropriate directories on their node.

Network Expansion: As more users establish Odin nodes, the network grows, increasing the availability and distribution of files across a broader range.

## Advantages of Odin Over Other Decentralized Solutions

1. Decentralized File Hosting with Federated Search
- Odin: Each node operates independently, hosting its own files and handling its own search queries. The federated search system aggregates results from multiple nodes, ensuring a comprehensive search experience without relying on a central tracker or indexer.
   
- BitTorrent/IPFS: Typically rely on centralized or semi-centralized trackers (BitTorrent) or distributed hash tables (IPFS) for indexing and search.

2. Simple Node Operation
- Odin: Nodes are lightweight and easy to set up, requiring only a simple configuration and basic file placement. No complex software or additional components are needed for hosting files or participating in the network.
- BitTorrent/IPFS: Can involve more complex setup processes and require additional software or configurations to function effectively.

3. No Need for Specialized Clients
- Odin: Operates over standard HTTP, allowing users to access and download files using any modern web browser. This eliminates the need for specialized clients or software.
- BitTorrent: Requires specific torrent clients to download files. IPFS requires IPFS clients or gateways for accessing content.

4. Rapidly Growing Network with Minimal Overhead
- Odin: Designed to scale effortlessly with the number of nodes, leveraging federated search to distribute query load and minimize individual node responsibilities.
- BitTorrent/IPFS: May experience performance issues with high numbers of peers or files, especially if nodes become heavily loaded with both data and queries.

5. Flexible File Access and Distribution
- Odin: Provides unrestricted access to files, with users able to download from any node hosting the desired content. There are no built-in restrictions on file availability.
- BitTorrent/IPFS: Often involve mechanisms for rate-limiting, seeding requirements, or access controls, which can restrict file availability and download speeds.

6. Admin-Controlled Content Compliance
- Odin: Content compliance is managed by individual node admins, who are responsible for handling copyright and DMCA issues according to their local regulations. This decentralized approach allows flexibility in content management.
- BitTorrent/IPFS: Content management is less flexible, with issues often handled by central entities or through network-wide policies.

7. Autocategorization Based on Path and Extension
- Odin: Automatically categorizes files based on their directory path and file extension, simplifying the organization and searchability of large datasets.
- BitTorrent/IPFS: Generally do not include built-in categorization features, relying on external metadata or user-added tags.

8. Efficient Peer Discovery
- Odin: Utilizes gossip-based peer discovery with a constant heartbeat ping to maintain an up-to-date list of active nodes, ensuring efficient network operation and node management.
- BitTorrent: Depends on trackers or DHT for peer discovery, which can be subject to central points of failure or inefficiencies. IPFS uses a similar DHT-based approach.

9. Community-Driven Expansion
- Odin: Leverages the contributions of data hoarders who bring substantial storage capacities to the network, creating a massive, distributed archive of information.
- BitTorrent/IPFS: Expansion often depends on broader adoption and community support, with no specific focus on data hoarders or large-scale individual contributions.

## Roadmap
### Minor Features

CSS and Multiple Themes: Implementation of customizable CSS and multiple themes to enhance user interface aesthetics.

Wiki and Usage Documentation: Comprehensive wiki and usage documents to assist users in setting up and utilizing Odin effectively.

### Major Features

Admin Panel: Development of a web-based admin panel for easier management and configuration of Odin nodes.

Proxying Nodes: Support for proxying one node over another, which is useful for nodes that cannot directly port forward, allowing for greater flexibility in network setup.

## Status

Odin is currently in early alpha. While the core features are functional, the project is still under development and is not yet ready for production use. We welcome feedback and contributions as we work towards a stable release.


