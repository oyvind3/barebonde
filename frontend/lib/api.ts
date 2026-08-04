const productionApiUrl = 'https://barebonde-ebf2byfnesgzaqgn.norwayeast-01.azurewebsites.net'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || (
  process.env.NODE_ENV === 'production' ? productionApiUrl : 'http://localhost:8000'
)
