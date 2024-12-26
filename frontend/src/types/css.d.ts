// src/types/css.d.ts

declare module '*.module.css' {
    const classes: {
      readonly [key: string]: string
    }
    export default classes
  }

  declare module '*.css' {
    const css: string
    export default css
  }

  declare module '*.scss' {
    const classes: {
      readonly [key: string]: string
    }
    export default classes
  }

  // Add support for other style formats if needed
  declare module '*.sass' {
    const classes: {
      readonly [key: string]: string
    }
    export default classes
  }

  declare module '*.less' {
    const classes: {
      readonly [key: string]: string
    }
    export default classes
  }
