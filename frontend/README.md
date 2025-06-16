# Market Overview Frontend

This is a React application built with Vite that displays a market overview by fetching data from a backend API. It shows information for various trading symbols, including current prices, technical indicators, and support/resistance levels.

## Styling

This project uses **Tailwind CSS** for utility-first styling. All components are styled using Tailwind classes.

### Dark/Light Mode

The application supports a dark/light mode theme.
-   Click the theme toggle button (usually located at the top-right of the page) to switch between dark and light modes.
-   Your preference will be saved in local storage and applied on subsequent visits.

## Development

### Prerequisites

- Node.js (v18.x or later recommended)
- npm (usually comes with Node.js) or yarn

### Installation

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    Using npm:
    ```bash
    npm install
    ```
    Or using yarn:
    ```bash
    yarn install
    ```

### Running the Development Server

1.  **Start the Vite development server:**
    Using npm:
    ```bash
    npm run dev
    ```
    Or using yarn:
    ```bash
    yarn dev
    ```
    This will usually start the application on `http://localhost:5173` (the port may vary if 5173 is in use). Tailwind CSS is compiled in real-time along with other assets.

### Building for Production

To create a production build:
Using npm:
```bash
npm run build
```
Or using yarn:
```bash
yarn build
```
Vite will handle the bundling and optimization of assets, including Tailwind CSS styles. No separate build steps are typically required for Tailwind CSS.

## Backend API

This frontend application expects the backend API to be running and accessible at:

-   **Base URL**: `http://localhost:8000`
-   **Market Overview Endpoint**: `GET /api/v1/market_overview`

Make sure the backend server is running and configured to allow requests from the frontend's origin if they are on different ports (CORS). The API endpoint is currently hardcoded in `src/api/market.js`.
