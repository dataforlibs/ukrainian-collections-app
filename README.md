# Украдені скарби (Stolen Treasures)

Interactive spatio-temporal visualization of Ukrainian artifacts in Russian museums.

## About

"Украдені скарби" (Stolen Treasures) is a collection created from resources gathered from Russian museums that have appropriated artifacts found on Ukrainian territory. This interactive catalog features a spatio-temporal interface that allows users to explore locations across different time periods and empires.

## Features

- 🗺️ **Interactive Map** - Visualize artifact locations across Ukraine
- ⏱️ **Timeline Streamgraph** - Filter artifacts by historical period
- 📊 **Two Museum Collections**:
  - State Historical Museum of Russia (Державний історичний музей Росії)
  - Hermitage Museum (Ермітаж)
- 🔍 **Zoom Controls** - Adjust visualization detail
- 📱 **Responsive Design** - Works on desktop and mobile

## Tech Stack

- **React 18** - UI framework
- **D3.js v7** - Data visualization
- **Vite** - Build tool and dev server
- **JavaScript (ES6+)** - Modern JavaScript

## Prerequisites

Before you begin, make sure you have installed:
- [Node.js](https://nodejs.org/) (version 16 or higher)
- npm (comes with Node.js)

To check if you have Node.js installed:
```bash
node --version
npm --version
```

## Installation

### Step 1: Install Dependencies

```bash
npm install
```

This will install all required packages listed in `package.json`.

### Step 2: Start Development Server

```bash
npm run dev
```

The app will open automatically at `http://localhost:3000`

## Available Scripts

### Development
```bash
npm run dev
```
Starts the development server with hot-reload.

### Production Build
```bash
npm run build
```
Creates an optimized production build in the `dist/` folder.

### Preview Production Build
```bash
npm run preview
```
Preview the production build locally.

### Lint
```bash
npm run lint
```
Check code for errors and style issues.

## Project Structure

```
ukrainian-collections-app/
├── public/                          # Static assets
│   ├── SHM_final_short.csv         # State Historical Museum data
│   ├── Hermitage_final_short.csv   # Hermitage Museum data
│   ├── stream.csv                  # Timeline data
│   ├── coordinates.json            # Location coordinates
│   └── geoBoundaries-UKR-ADM0_simplified.geojson  # Ukraine borders
├── src/
│   ├── App.jsx                     # Main application component
│   ├── main.jsx                    # React entry point
│   └── index.css                   # Global styles
├── index.html                       # HTML entry point
├── package.json                     # Project configuration
├── vite.config.js                  # Vite configuration
└── README.md                        # This file
```

## Data Files

All data files are located in the `public/` directory:

- **SHM_final_short.csv** - 77,536 artifacts from State Historical Museum
- **Hermitage_final_short.csv** - Artifacts from Hermitage Museum
- **stream.csv** - Temporal distribution data for the streamgraph
- **coordinates.json** - Geographic coordinates for artifact locations
- **geoBoundaries-UKR-ADM0_simplified.geojson** - Ukraine border geometry

## Usage

1. **Select Time Period**: Drag the brush on the timeline to filter artifacts by date
2. **View Artifacts**: Click on circles on the map to see artifact details
3. **Switch Museums**: Use the tabs to view different museum collections
4. **Zoom**: Use +/- buttons to adjust circle sizes

## Deployment

### Build for Production

```bash
npm run build
```

This creates a `dist/` folder with optimized files ready for deployment.

### Deploy to Static Hosting

The built files in `dist/` can be deployed to any static hosting service:

- **GitHub Pages**: Use [gh-pages](https://www.npmjs.com/package/gh-pages)
- **Netlify**: Drag and drop the `dist/` folder
- **Vercel**: Import the repository
- **Cloudflare Pages**: Connect your Git repository

Example for GitHub Pages:
```bash
npm install --save-dev gh-pages

# Add to package.json scripts:
# "deploy": "gh-pages -d dist"

npm run build
npm run deploy
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Contributing

This project maintains the original metadata language (Russian) from the museum collections, with Ukrainian interface text added by Ukrainian journalists.

## License

MIT License - See LICENSE file for details

## Credits

- **Original Project**: [Dataforlibs](https://dataforlibs.github.io)
- **Publication**: [Texty.org - Stolen Treasures](https://texty.org.ua/d/2023/stolen_heritage/)

## Copyright Notice

No copyright is claimed for artifact images and metadata posted on this site. In cases where use of materials may appear as potential infringement, we believe that interactive spatio-temporal visualization of collections is fair use under the principles of fair use provided by U.S. and Canadian copyright laws.

---

© Dataforlibs 2025
# ukrainian-collections-app
